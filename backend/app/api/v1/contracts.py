import logging
import os
from calendar import monthrange
from datetime import datetime, timezone, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models.client import Client
from app.models.contract import Contract
from app.models.payment import Payment
from app.models.trial_booking import TrialBooking
from app.models.user import User
from app.services.pdf import generate_contract_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contracts", tags=["contracts"])


class IntakeData(BaseModel):
    intake_token: str
    child_name: str
    child_birth_date: date
    parent_name: str
    parent_phone: str
    passport_data: str
    amount: float = 5000.0


class ContractOut(BaseModel):
    id: int
    client_id: int
    amount: float
    status: str
    created_at: datetime
    pdf_path: Optional[str]

    class Config:
        from_attributes = True


@router.post("/intake", summary="Приём анкеты и генерация договора")
async def intake(
    data: IntakeData,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TrialBooking).where(TrialBooking.intake_token == data.intake_token)
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(404, "Анкета не найдена или ссылка устарела")

    client = Client(
        lead_id=booking.lead_id,
        child_name=data.child_name,
        child_birth_date=data.child_birth_date,
        parent_name=data.parent_name,
        parent_phone=data.parent_phone,
        passport_data=data.passport_data,
    )
    db.add(client)
    await db.flush()

    contract = Contract(client_id=client.id, amount=data.amount)
    db.add(contract)
    await db.flush()

    try:
        pdf_path = await generate_contract_pdf(client, contract)
        contract.pdf_path = pdf_path
    except Exception as e:
        logger.error("PDF generation failed: %s", e)

    await db.commit()
    logger.info("Contract created for client %s", client.id)
    return {
        "message": "Спасибо! Ваш договор готов, менеджер распечатает его к вашему приходу.",
        "contract_id": contract.id,
    }


@router.get("", response_model=List[ContractOut], summary="Список договоров")
async def list_contracts(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Contract).order_by(Contract.created_at.desc()))
    return result.scalars().all()


@router.get("/{contract_id}", response_model=ContractOut, summary="Договор по ID")
async def get_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Договор не найден")
    return c


@router.get("/{contract_id}/download", summary="Скачать PDF договора")
async def download_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    c = result.scalar_one_or_none()
    if not c or not c.pdf_path:
        raise HTTPException(404, "PDF не найден")
    if not os.path.exists(c.pdf_path):
        raise HTTPException(404, "Файл не найден на диске")
    return FileResponse(c.pdf_path, media_type="application/pdf", filename=f"contract_{contract_id}.pdf")


@router.post("/{contract_id}/sign", summary="Зафиксировать подписание")
async def sign_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(404, "Договор не найден")
    if c.status == "signed":
        raise HTTPException(409, "Договор уже подписан")

    now = datetime.now(timezone.utc)
    c.status = "signed"
    c.signed_at = now

    # Activate client
    client_result = await db.execute(select(Client).where(Client.id == c.client_id))
    client = client_result.scalar_one_or_none()
    if client:
        client.status = "active"

        # Create first month payment record
        today = now.date()
        last_day = monthrange(today.year, today.month)[1]
        period_to = today.replace(day=last_day)
        payment = Payment(
            client_id=client.id,
            amount=float(c.amount),
            period_from=today,
            period_to=period_to,
            status="pending",
        )
        db.add(payment)

        # Send welcome notification
        from app.services.notifications import notify_lead
        from app.models.lead import Lead
        lead_result = await db.execute(select(Lead).where(Lead.id == client.lead_id))
        lead = lead_result.scalar_one_or_none()
        if lead and lead.telegram_chat_id:
            await notify_lead(
                db,
                lead.id,
                lead.telegram_chat_id,
                f"Добро пожаловать в KiberOne, {client.child_name}! Договор подписан. Ждём вас на занятиях!",
            )

    await db.commit()
    logger.info("Contract %s signed, client %s activated", contract_id, c.client_id)
    return {"status": "signed", "contract_id": contract_id}
