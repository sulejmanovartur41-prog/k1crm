import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Integer, select, func, cast
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, require_role
from app.database import get_db
from app.models.attendance import Attendance
from app.models.client import Client
from app.models.group import Group
from app.models.lesson import Lesson
from app.models.payment import Payment
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/groups", tags=["groups"])

GroupStatus = Literal["active", "archived"]


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    level: Optional[str] = Field(default=None, max_length=50)
    teacher_id: Optional[int] = None
    room: Optional[str] = Field(default=None, max_length=50)
    capacity: int = Field(default=12, ge=1, le=100)
    color: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = Field(default=None, max_length=500)


class GroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    level: Optional[str] = Field(default=None, max_length=50)
    teacher_id: Optional[int] = None
    room: Optional[str] = Field(default=None, max_length=50)
    capacity: Optional[int] = Field(default=None, ge=1, le=100)
    color: Optional[str] = Field(default=None, max_length=20)
    description: Optional[str] = Field(default=None, max_length=500)
    status: Optional[GroupStatus] = None


class GroupOut(BaseModel):
    id: int
    name: str
    level: Optional[str]
    teacher_id: Optional[int]
    room: Optional[str]
    capacity: int
    color: Optional[str]
    status: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class GroupListItem(GroupOut):
    students_count: int
    teacher_name: Optional[str]


class GroupStudent(BaseModel):
    id: int
    child_name: str
    child_birth_date: Optional[date]
    parent_name: str
    parent_phone: str
    status: str
    attendance_rate: Optional[float]   # % present за последние 30 дней, None если уроков не было
    payment_status: Optional[str]      # статус последнего платежа


class GroupLessonItem(BaseModel):
    id: int
    datetime: datetime
    room: Optional[str]
    capacity: int


class GroupDetail(GroupOut):
    teacher_name: Optional[str]
    students: List[GroupStudent]
    upcoming_lessons: List[GroupLessonItem]


async def _validate_teacher(db: AsyncSession, teacher_id: Optional[int]) -> None:
    if teacher_id is None:
        return
    res = await db.execute(select(User).where(User.id == teacher_id))
    teacher = res.scalar_one_or_none()
    if not teacher:
        raise HTTPException(422, "Преподаватель не найден")
    if teacher.role != "teacher":
        raise HTTPException(422, "Указанный пользователь не имеет роли преподавателя")


@router.get("", response_model=List[GroupListItem], summary="Список групп")
async def list_groups(
    status: Optional[GroupStatus] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # admin/manager — все группы, teacher — только свои (включая archived,
    # чтобы видеть прошлогодний контекст). Фильтр status опциональный.
    q = (
        select(
            Group,
            func.count(Client.id).label("students_count"),
            User.name.label("teacher_name"),
        )
        .outerjoin(Client, Client.group_id == Group.id)
        .outerjoin(User, User.id == Group.teacher_id)
        .group_by(Group.id, User.name)
        .order_by(Group.name)
    )
    if current_user.role == "teacher":
        q = q.where(Group.teacher_id == current_user.id)
    if status is not None:
        q = q.where(Group.status == status)

    result = await db.execute(q)
    items = []
    for group, students_count, teacher_name in result.all():
        item = GroupListItem(
            **GroupOut.model_validate(group).model_dump(),
            students_count=students_count or 0,
            teacher_name=teacher_name,
        )
        items.append(item)
    return items


@router.get("/{group_id}", response_model=GroupDetail, summary="Карточка группы")
async def get_group(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(select(Group).where(Group.id == group_id))
    group = res.scalar_one_or_none()
    if not group:
        raise HTTPException(404, "Группа не найдена")
    if current_user.role == "teacher" and group.teacher_id != current_user.id:
        raise HTTPException(403, "Доступ только к своим группам")

    teacher_name = None
    if group.teacher_id is not None:
        t_res = await db.execute(select(User.name).where(User.id == group.teacher_id))
        teacher_name = t_res.scalar_one_or_none()

    students_res = await db.execute(
        select(Client)
        .where(Client.group_id == group_id)
        .order_by(Client.child_name)
    )
    raw_students = students_res.scalars().all()

    # Attendance stats for the last 30 days: lessons in [cutoff, now]
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    att_res = await db.execute(
        select(
            Attendance.client_id,
            func.count().label("total"),
            func.sum(cast(Attendance.present, Integer)).label("present_count"),
        )
        .join(Lesson, Lesson.id == Attendance.lesson_id)
        .where(
            Attendance.client_id.in_([c.id for c in raw_students]),
            Lesson.group_id == group_id,
            Lesson.datetime >= cutoff,
        )
        .group_by(Attendance.client_id)
    )
    # Fraction 0-1 (same representation as dashboard attendance_by_group.rate)
    att_map: dict[int, float] = {}
    for client_id, total, present_count in att_res.all():
        att_map[client_id] = round((present_count or 0) / total, 2) if total else 0.0

    # Last payment status per student
    pay_res = await db.execute(
        select(Payment.client_id, Payment.status)
        .where(Payment.client_id.in_([c.id for c in raw_students]))
        .order_by(Payment.client_id, Payment.created_at.desc())
    )
    pay_map: dict[int, str] = {}
    for client_id, pay_status in pay_res.all():
        if client_id not in pay_map:
            pay_map[client_id] = pay_status

    students = [
        GroupStudent(
            id=c.id,
            child_name=c.child_name,
            child_birth_date=c.child_birth_date,
            parent_name=c.parent_name,
            parent_phone=c.parent_phone,
            status=c.status,
            attendance_rate=att_map.get(c.id),
            payment_status=pay_map.get(c.id),
        )
        for c in raw_students
    ]

    now = datetime.now(timezone.utc)
    lessons_res = await db.execute(
        select(Lesson)
        .where(Lesson.group_id == group_id, Lesson.datetime >= now)
        .order_by(Lesson.datetime)
        .limit(5)
    )
    upcoming = [
        GroupLessonItem(id=l.id, datetime=l.datetime, room=l.room, capacity=l.capacity)
        for l in lessons_res.scalars().all()
    ]

    return GroupDetail(
        **GroupOut.model_validate(group).model_dump(),
        teacher_name=teacher_name,
        students=students,
        upcoming_lessons=upcoming,
    )


@router.post("", response_model=GroupOut, status_code=201, summary="Создать группу")
async def create_group(
    data: GroupCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "manager")),
):
    await _validate_teacher(db, data.teacher_id)
    group = Group(**data.model_dump())
    db.add(group)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Группа с таким названием уже существует")
    await db.refresh(group)
    logger.info("Group created: %s (id=%s)", group.name, group.id)
    return group


@router.patch("/{group_id}", response_model=GroupOut, summary="Изменить группу")
async def update_group(
    group_id: int,
    data: GroupUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "manager")),
):
    res = await db.execute(select(Group).where(Group.id == group_id))
    group = res.scalar_one_or_none()
    if not group:
        raise HTTPException(404, "Группа не найдена")

    payload = data.model_dump(exclude_unset=True)
    if "teacher_id" in payload:
        await _validate_teacher(db, payload["teacher_id"])
    for field, value in payload.items():
        setattr(group, field, value)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Группа с таким названием уже существует")
    await db.refresh(group)
    return group


@router.post("/{group_id}/students/{client_id}", status_code=204, summary="Добавить ученика в группу")
async def add_student(
    group_id: int,
    client_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "manager")),
):
    g_res = await db.execute(select(Group).where(Group.id == group_id))
    if not g_res.scalar_one_or_none():
        raise HTTPException(404, "Группа не найдена")
    c_res = await db.execute(select(Client).where(Client.id == client_id))
    client = c_res.scalar_one_or_none()
    if not client:
        raise HTTPException(404, "Клиент не найден")
    client.group_id = group_id
    await db.commit()


class ScheduleGenRequest(BaseModel):
    weekdays: List[int] = Field(..., description="ISO weekdays: 1=Пн … 7=Вс", min_length=1)
    time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="Время урока HH:MM")
    weeks: int = Field(default=8, ge=1, le=52)
    start_date: Optional[date] = None


@router.post("/{group_id}/schedule", summary="Сгенерировать расписание")
async def generate_schedule(
    group_id: int,
    data: ScheduleGenRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "manager")),
):
    res = await db.execute(select(Group).where(Group.id == group_id))
    group = res.scalar_one_or_none()
    if not group:
        raise HTTPException(404, "Группа не найдена")
    if group.teacher_id is None:
        raise HTTPException(422, "Назначьте преподавателя перед генерацией расписания")

    hour, minute = map(int, data.time.split(":"))
    start = data.start_date or date.today()

    existing_res = await db.execute(
        select(Lesson.datetime).where(Lesson.group_id == group_id)
    )
    existing_dates = {row[0].date() for row in existing_res.all() if row[0]}

    def first_occurrence(iso_wd: int) -> date:
        delta = (iso_wd - 1) - start.weekday()
        if delta < 0:
            delta += 7
        return start + timedelta(days=delta)

    created = 0
    skipped: list[str] = []

    for wd in data.weekdays:
        current = first_occurrence(wd)
        for week in range(data.weeks):
            target = current + timedelta(weeks=week)
            if target in existing_dates:
                skipped.append(str(target))
                continue
            db.add(Lesson(
                group_id=group_id,
                teacher_id=group.teacher_id,
                datetime=datetime(target.year, target.month, target.day, hour, minute, tzinfo=timezone.utc),
                room=group.room,
                capacity=group.capacity,
            ))
            existing_dates.add(target)  # prevent duplicate within same request
            created += 1

    await db.commit()
    logger.info("Schedule generated for group %s: created=%s skipped=%s", group_id, created, len(skipped))
    return {"created": created, "skipped": skipped}


@router.delete("/{group_id}/students/{client_id}", status_code=204, summary="Убрать ученика из группы")
async def remove_student(
    group_id: int,
    client_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "manager")),
):
    c_res = await db.execute(select(Client).where(Client.id == client_id))
    client = c_res.scalar_one_or_none()
    if not client:
        raise HTTPException(404, "Клиент не найден")
    if client.group_id != group_id:
        raise HTTPException(409, "Клиент не состоит в этой группе")
    client.group_id = None
    await db.commit()
