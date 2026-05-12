from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models.attendance import Attendance
from app.models.client import Client
from app.models.contract import Contract
from app.models.lesson import Lesson
from app.models.payment import Payment
from app.models.user import User

router = APIRouter(prefix="/clients", tags=["clients"])


class PaymentItem(BaseModel):
    id: int
    amount: float
    period_from: date
    period_to: date
    status: str
    method: Optional[str]
    paid_at: Optional[datetime]


class AttendanceItem(BaseModel):
    lesson_id: int
    lesson_datetime: datetime
    present: bool


class ContractInfo(BaseModel):
    id: int
    status: str
    amount: float
    signed_at: Optional[datetime]
    pdf_path: Optional[str]


class ClientDetails(BaseModel):
    id: int
    child_name: str
    child_birth_date: date
    parent_name: str
    parent_phone: str
    passport_data: Optional[str]
    status: str
    group_id: Optional[int]
    created_at: datetime
    payments: List[PaymentItem]
    attendance: List[AttendanceItem]
    contract: Optional[ContractInfo]


@router.get("/{client_id}/details", response_model=ClientDetails, summary="Карточка ученика")
async def client_details(
    client_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(select(Client).where(Client.id == client_id))
    client = res.scalar_one_or_none()
    if not client:
        raise HTTPException(404, "Клиент не найден")

    # RBAC: teacher может смотреть только учеников из своих групп
    if current_user.role == "teacher":
        if client.group_id is None:
            raise HTTPException(403, "Доступ запрещён")
        from app.models.group import Group
        g_res = await db.execute(select(Group).where(Group.id == client.group_id))
        group = g_res.scalar_one_or_none()
        if not group or group.teacher_id != current_user.id:
            raise HTTPException(403, "Доступ только к ученикам своих групп")

    # Последние 6 платежей
    pay_res = await db.execute(
        select(Payment)
        .where(Payment.client_id == client_id)
        .order_by(Payment.created_at.desc())
        .limit(6)
    )
    payments = [
        PaymentItem(
            id=p.id,
            amount=float(p.amount),
            period_from=p.period_from,
            period_to=p.period_to,
            status=p.status,
            method=p.method,
            paid_at=p.paid_at,
        )
        for p in pay_res.scalars().all()
    ]

    # Последние 20 записей посещаемости
    att_res = await db.execute(
        select(Attendance, Lesson.datetime)
        .join(Lesson, Lesson.id == Attendance.lesson_id)
        .where(Attendance.client_id == client_id)
        .order_by(Lesson.datetime.desc())
        .limit(20)
    )
    attendance = [
        AttendanceItem(
            lesson_id=a.lesson_id,
            lesson_datetime=lesson_dt,
            present=a.present,
        )
        for a, lesson_dt in att_res.all()
    ]

    # Договор
    contract = None
    con_res = await db.execute(
        select(Contract)
        .where(Contract.client_id == client_id)
        .order_by(Contract.created_at.desc())
        .limit(1)
    )
    con = con_res.scalar_one_or_none()
    if con:
        contract = ContractInfo(
            id=con.id,
            status=con.status,
            amount=float(con.amount),
            signed_at=con.signed_at,
            pdf_path=con.pdf_path,
        )

    return ClientDetails(
        id=client.id,
        child_name=client.child_name,
        child_birth_date=client.child_birth_date,
        parent_name=client.parent_name,
        parent_phone=client.parent_phone,
        passport_data=client.passport_data,
        status=client.status,
        group_id=client.group_id,
        created_at=client.created_at,
        payments=payments,
        attendance=attendance,
        contract=contract,
    )
