import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, require_role
from app.database import get_db
from app.models.lesson import Lesson
from app.models.trial_booking import TrialBooking
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedule", tags=["schedule"])


class LessonCreate(BaseModel):
    group_name: str
    teacher_id: int
    datetime: datetime
    room: Optional[str] = None
    capacity: int = 12


class LessonOut(BaseModel):
    id: int
    group_name: str
    teacher_id: int
    datetime: datetime
    room: Optional[str]
    capacity: int

    class Config:
        from_attributes = True


class BookingCreate(BaseModel):
    lead_id: int
    lesson_id: int


class BookingOut(BaseModel):
    id: int
    lead_id: int
    lesson_id: int
    status: str
    intake_token: Optional[str]

    class Config:
        from_attributes = True


@router.get("/lessons", response_model=List[LessonOut], summary="Список занятий")
async def list_lessons(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Lesson).order_by(Lesson.datetime))
    return result.scalars().all()


@router.post("/lessons", response_model=LessonOut, status_code=201, summary="Создать занятие")
async def create_lesson(
    data: LessonCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "manager")),
):
    lesson = Lesson(**data.model_dump())
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    return lesson


@router.get("/lessons/{lesson_id}/slots", summary="Свободные слоты")
async def get_slots(
    lesson_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(404, "Занятие не найдено")
    booked = await db.execute(
        select(func.count(TrialBooking.id)).where(
            TrialBooking.lesson_id == lesson_id,
            TrialBooking.status == "booked",
        )
    )
    booked_count = booked.scalar()
    return {
        "lesson_id": lesson_id,
        "capacity": lesson.capacity,
        "booked": booked_count,
        "free": lesson.capacity - booked_count,
    }


@router.post("/bookings", response_model=BookingOut, status_code=201, summary="Записать на пробный урок")
async def create_booking(
    data: BookingCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Lesson).where(Lesson.id == data.lesson_id))
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(404, "Занятие не найдено")

    booked = await db.execute(
        select(func.count(TrialBooking.id)).where(
            TrialBooking.lesson_id == data.lesson_id,
            TrialBooking.status == "booked",
        )
    )
    if booked.scalar() >= lesson.capacity:
        raise HTTPException(409, "Нет свободных мест на занятии")

    token = secrets.token_urlsafe(32)
    booking = TrialBooking(lead_id=data.lead_id, lesson_id=data.lesson_id, intake_token=token)
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    logger.info("Trial booking created: lead=%s lesson=%s", data.lead_id, data.lesson_id)

    # Schedule reminders at 24h and 2h before lesson
    from app.tasks.calls import send_trial_reminder
    now = datetime.now(timezone.utc)
    lesson_dt = lesson.datetime
    if hasattr(lesson_dt, 'tzinfo') and lesson_dt.tzinfo is None:
        lesson_dt = lesson_dt.replace(tzinfo=timezone.utc)

    eta_24h = lesson_dt - timedelta(hours=24)
    eta_2h = lesson_dt - timedelta(hours=2)

    if eta_24h > now:
        send_trial_reminder.apply_async((booking.id, 24), eta=eta_24h)
    if eta_2h > now:
        send_trial_reminder.apply_async((booking.id, 2), eta=eta_2h)

    return booking


@router.patch("/bookings/{booking_id}", summary="Изменить/отменить запись")
async def update_booking(
    booking_id: int,
    status: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(TrialBooking).where(TrialBooking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(404, "Запись не найдена")
    booking.status = status
    await db.commit()
    return {"status": "ok"}
