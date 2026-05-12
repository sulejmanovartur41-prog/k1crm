import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, require_role
from app.database import get_db
from app.models.attendance import Attendance
from app.models.client import Client
from app.models.lesson import Lesson
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/attendance", tags=["attendance"])


class AttendanceMark(BaseModel):
    client_id: int
    present: bool


class MarkRequest(BaseModel):
    marks: List[AttendanceMark]


class AttendanceOut(BaseModel):
    id: int
    lesson_id: int
    client_id: int
    present: bool
    marked_at: datetime

    class Config:
        from_attributes = True


@router.get("/lessons/{lesson_id}", summary="Список учеников занятия")
async def get_lesson_students(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(404, "Занятие не найдено")
    # Учитель видит только свои занятия
    if current_user.role == "teacher" and lesson.teacher_id != current_user.id:
        raise HTTPException(403, "Доступ только к своим занятиям")

    # Список учеников ограничен группой урока — учитель не должен видеть
    # детей из других групп. Если клиент ещё не прикреплён к группе
    # (group_name IS NULL) — он не попадёт в список переклички.
    att_result = await db.execute(
        select(Attendance).where(Attendance.lesson_id == lesson_id)
    )
    existing = {a.client_id: a for a in att_result.scalars().all()}

    clients_result = await db.execute(
        select(Client).where(
            Client.status == "active",
            Client.group_name == lesson.group_name,
        )
    )
    clients = clients_result.scalars().all()

    return [
        {
            "client_id": c.id,
            "child_name": c.child_name,
            "parent_name": c.parent_name,
            "present": existing[c.id].present if c.id in existing else None,
        }
        for c in clients
    ]


@router.post("/lessons/{lesson_id}/mark", summary="Отметить посещаемость")
async def mark_attendance(
    lesson_id: int,
    body: MarkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "teacher")),
):
    # Достаём урок (нужен и для проверки teacher_id, и для cross-group защиты).
    lesson_res = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = lesson_res.scalar_one_or_none()
    if not lesson:
        raise HTTPException(404, "Занятие не найдено")
    if current_user.role == "teacher" and lesson.teacher_id != current_user.id:
        raise HTTPException(403, "Доступ только к своим занятиям")

    # Авторизация по группе: учитель не должен мочь подсунуть client_id ребёнка
    # из чужой группы. Список GET /attendance/lessons/{id} это уже фильтровал,
    # но POST /mark до сих пор принимал произвольные client_id.
    requested_ids = [m.client_id for m in body.marks]
    if requested_ids:
        valid_res = await db.execute(
            select(Client.id).where(
                Client.id.in_(requested_ids),
                Client.group_name == lesson.group_name,
            )
        )
        valid_ids = {row[0] for row in valid_res.all()}
        invalid = set(requested_ids) - valid_ids
        if invalid:
            raise HTTPException(
                422,
                f"Клиенты {sorted(invalid)} не принадлежат группе урока",
            )

    now = datetime.now(timezone.utc)
    for mark in body.marks:
        result = await db.execute(
            select(Attendance).where(
                Attendance.lesson_id == lesson_id,
                Attendance.client_id == mark.client_id,
            )
        )
        record = result.scalar_one_or_none()
        if record:
            record.present = mark.present
            record.marked_at = now
            record.marked_by = current_user.id
        else:
            db.add(Attendance(
                lesson_id=lesson_id,
                client_id=mark.client_id,
                present=mark.present,
                marked_by=current_user.id,
            ))

    try:
        await db.commit()
    except IntegrityError:
        # Гонка: параллельный POST с другого устройства уже создал
        # Attendance — UNIQUE-constraint срабатывает. Откатываем и
        # повторяем как чистый UPDATE.
        await db.rollback()
        for mark in body.marks:
            result = await db.execute(
                select(Attendance).where(
                    Attendance.lesson_id == lesson_id,
                    Attendance.client_id == mark.client_id,
                )
            )
            record = result.scalar_one_or_none()
            if record:
                record.present = mark.present
                record.marked_at = now
                record.marked_by = current_user.id
        await db.commit()
    logger.info("Attendance marked for lesson %s by user %s", lesson_id, current_user.id)

    # Trigger payment check (Celery would be used in production)
    from app.tasks.payments import check_payment_for_lesson
    check_payment_for_lesson.delay(lesson_id)

    return {"status": "ok", "marked": len(body.marks)}


@router.get("/clients/{client_id}", summary="История посещаемости клиента")
async def client_attendance(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Attendance).where(Attendance.client_id == client_id).order_by(Attendance.marked_at.desc())
    )
    records = result.scalars().all()
    return [{"lesson_id": r.lesson_id, "present": r.present, "marked_at": r.marked_at} for r in records]
