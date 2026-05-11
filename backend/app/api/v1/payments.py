import logging
from datetime import datetime, timezone, date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models.attendance import Attendance
from app.models.client import Client
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
    _: User = Depends(get_current_user),
):
    q = select(Payment).order_by(Payment.created_at.desc())
    if status:
        q = q.where(Payment.status == status)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/overdue", summary="Список должников")
async def list_overdue(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Payment).where(Payment.status.in_(["overdue", "pending"]))
    )
    return result.scalars().all()


@router.get("/dashboard", summary="Дашборд выручки и аналитики")
async def dashboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    month_start = now.date().replace(day=1)
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    # Revenue current month
    rev_current = await db.execute(
        select(func.sum(Payment.amount)).where(
            Payment.status == "paid",
            Payment.paid_at >= datetime.combine(month_start, datetime.min.time()).replace(tzinfo=timezone.utc),
        )
    )
    rev_current_val = float(rev_current.scalar() or 0)

    # Revenue previous month
    rev_prev = await db.execute(
        select(func.sum(Payment.amount)).where(
            Payment.status == "paid",
            Payment.paid_at >= datetime.combine(prev_month_start, datetime.min.time()).replace(tzinfo=timezone.utc),
            Payment.paid_at < datetime.combine(month_start, datetime.min.time()).replace(tzinfo=timezone.utc),
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
        select(func.count(Lead.id)).where(Lead.status.in_(["enrolled", "archived"]))
    )

    total = total_leads.scalar() or 0
    converted = converted_leads.scalar() or 0

    # Funnel: leads by status
    funnel_result = await db.execute(
        select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
    )
    funnel = [{"status": row[0], "count": row[1]} for row in funnel_result.all()]

    # Weekly revenue: last 12 weeks
    weekly_revenue = []
    for i in range(11, -1, -1):
        week_start = now - timedelta(weeks=i + 1)
        week_end = now - timedelta(weeks=i)
        wr = await db.execute(
            select(func.sum(Payment.amount)).where(
                Payment.status == "paid",
                Payment.paid_at >= week_start,
                Payment.paid_at < week_end,
            )
        )
        iso_week = (now - timedelta(weeks=i)).isocalendar()
        weekly_revenue.append({
            "week": f"{iso_week.year}-W{iso_week.week:02d}",
            "amount": float(wr.scalar() or 0),
        })

    # Attendance by group: last 30 days
    thirty_days_ago = now - timedelta(days=30)
    lessons_result = await db.execute(
        select(Lesson).where(Lesson.datetime >= thirty_days_ago)
    )
    lessons = lessons_result.scalars().all()

    attendance_by_group: dict[str, dict] = {}
    for lesson in lessons:
        grp = lesson.group_name
        if grp not in attendance_by_group:
            attendance_by_group[grp] = {"present": 0, "total": 0}
        att_result = await db.execute(
            select(Attendance).where(Attendance.lesson_id == lesson.id)
        )
        records = att_result.scalars().all()
        attendance_by_group[grp]["total"] += len(records)
        attendance_by_group[grp]["present"] += sum(1 for r in records if r.present)

    attendance_data = [
        {
            "group": grp,
            "rate": round(v["present"] / v["total"], 2) if v["total"] else 0,
        }
        for grp, v in attendance_by_group.items()
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
    _: User = Depends(get_current_user),
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
    await db.commit()
    await db.refresh(payment)
    logger.info("Payment recorded: client=%s amount=%s", data.client_id, data.amount)
    return payment


@router.get("/clients/{client_id}", summary="История оплат клиента")
async def client_payments(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Payment).where(Payment.client_id == client_id).order_by(Payment.created_at.desc())
    )
    return result.scalars().all()
