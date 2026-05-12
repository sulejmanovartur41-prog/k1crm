import logging
from datetime import datetime, timezone, date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, Integer
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, require_role
from app.database import get_db
from app.models.attendance import Attendance
from app.models.client import Client
from app.models.group import Group
from app.models.lead import Lead
from app.models.lesson import Lesson
from app.models.payment import Payment
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


class PaymentCreate(BaseModel):
    client_id: int
    amount: float
    period_from: date
    period_to: date
    method: str  # cash, qr


class PaymentOut(BaseModel):
    id: int
    client_id: int
    amount: float
    period_from: date
    period_to: date
    paid_at: Optional[datetime]
    status: str
    method: Optional[str]

    class Config:
        from_attributes = True


@router.get("", response_model=List[PaymentOut], summary="Все оплаты")
async def list_payments(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "manager")),
):
    q = select(Payment).order_by(Payment.created_at.desc())
    if status:
        q = q.where(Payment.status == status)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/overdue", summary="Список должников")
async def list_overdue(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "manager")),
):
    result = await db.execute(
        select(Payment).where(Payment.status.in_(["overdue", "pending"]))
    )
    return result.scalars().all()


@router.get("/dashboard", summary="Дашборд выручки и аналитики")
async def dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    now = datetime.now(timezone.utc)
    today = now.date()
    month_start = today.replace(day=1)
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    def at_utc(d: date) -> datetime:
        return datetime.combine(d, datetime.min.time()).replace(tzinfo=timezone.utc)

    # AsyncSession не безопасен для конкурентных execute() с одной транзакцией —
    # asyncpg бросит "concurrent operation". Поэтому используем последовательность,
    # но с явной группировкой: вычисления, не зависящие друг от друга, идут одним
    # SQL запросом через UNION ALL/CTE там, где это даёт выигрыш.
    # Запросы оставлены последовательными, но переписаны компактнее.

    prev_window_end = prev_month_start + timedelta(days=(today - month_start).days + 1)
    if prev_window_end > prev_month_end + timedelta(days=1):
        prev_window_end = prev_month_end + timedelta(days=1)

    rev_current = await db.execute(
        select(func.sum(Payment.amount)).where(
            Payment.status == "paid",
            Payment.paid_at >= at_utc(month_start),
        )
    )
    rev_current_val = float(rev_current.scalar() or 0)

    rev_prev = await db.execute(
        select(func.sum(Payment.amount)).where(
            Payment.status == "paid",
            Payment.paid_at >= at_utc(prev_month_start),
            Payment.paid_at < at_utc(prev_window_end),
        )
    )
    rev_prev_val = float(rev_prev.scalar() or 0)
    delta_pct = round((rev_current_val - rev_prev_val) / rev_prev_val * 100, 1) if rev_prev_val else 0

    active_clients = await db.execute(
        select(func.count(Client.id)).where(Client.status == "active")
    )
    overdue_count = await db.execute(
        select(func.count(Payment.id)).where(Payment.status.in_(["overdue", "pending"]))
    )
    total_leads = await db.execute(select(func.count(Lead.id)))
    converted_leads = await db.execute(
        select(func.count(Lead.id)).where(Lead.status == "enrolled")
    )

    total = total_leads.scalar() or 0
    converted = converted_leads.scalar() or 0

    # Funnel: leads by status
    funnel_result = await db.execute(
        select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
    )
    funnel = [{"status": row[0], "count": row[1]} for row in funnel_result.all()]

    # Weekly revenue: last 12 weeks — один SQL запрос, агрегация по неделям в Python
    # (для портативности между PostgreSQL и SQLite — date_trunc не работает в SQLite)
    weeks_start = now - timedelta(weeks=12)
    raw = await db.execute(
        select(Payment.paid_at, Payment.amount).where(
            Payment.status == "paid",
            Payment.paid_at >= weeks_start,
        )
    )
    weeks_buckets: dict[str, float] = {}
    for paid_at, amount in raw.all():
        if not paid_at:
            continue
        iso = paid_at.isocalendar()
        key = f"{iso.year}-W{iso.week:02d}"
        weeks_buckets[key] = weeks_buckets.get(key, 0.0) + float(amount)
    weekly_revenue = [
        {"week": k, "amount": v} for k, v in sorted(weeks_buckets.items())
    ]

    # Attendance by group: один SQL запрос с JOIN и GROUP BY
    thirty_days_ago = now - timedelta(days=30)
    att_raw = await db.execute(
        select(
            Group.name.label("group_name"),
            func.count(Attendance.id).label("total"),
            func.sum(func.cast(Attendance.present, Integer)).label("present"),
        )
        .join(Lesson, Lesson.id == Attendance.lesson_id)
        .join(Group, Group.id == Lesson.group_id)
        .where(Lesson.datetime >= thirty_days_ago)
        .group_by(Group.name)
    )
    attendance_data = [
        {
            "group": row.group_name,
            "rate": round((row.present or 0) / row.total, 2) if row.total else 0,
        }
        for row in att_raw.all()
    ]

    return {
        "revenue": {
            "current": rev_current_val,
            "prev": rev_prev_val,
            "delta_pct": delta_pct,
        },
        "active_clients": active_clients.scalar(),
        "overdue_count": overdue_count.scalar(),
        "lead_conversion": {
            "total": total,
            "converted": converted,
            "rate": round(converted / total, 3) if total else 0,
        },
        "funnel": funnel,
        "weekly_revenue": weekly_revenue,
        "attendance_by_group": attendance_data,
    }


@router.post("", response_model=PaymentOut, status_code=201, summary="Внести оплату")
async def create_payment(
    data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "manager")),
):
    payment = Payment(
        client_id=data.client_id,
        amount=data.amount,
        period_from=data.period_from,
        period_to=data.period_to,
        method=data.method,
        status="paid",
        paid_at=datetime.now(timezone.utc),
    )
    db.add(payment)
    try:
        await db.commit()
    except IntegrityError:
        # Сработал uq_payment_client_period — оплата за этот период уже есть.
        await db.rollback()
        raise HTTPException(409, "Оплата за этот период уже зафиксирована")
    await db.refresh(payment)
    logger.info("Payment recorded: client=%s amount=%s", data.client_id, data.amount)
    return payment


@router.get("/clients/{client_id}", summary="История оплат клиента")
async def client_payments(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "manager")),
):
    result = await db.execute(
        select(Payment).where(Payment.client_id == client_id).order_by(Payment.created_at.desc())
    )
    return result.scalars().all()
