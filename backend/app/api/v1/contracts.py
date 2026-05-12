import logging
import os
from calendar import monthrange
from datetime import datetime, timedelta, timezone, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, require_role
from app.config import settings
from app.database import get_db
from app.models.client import Client
from app.models.contract import Contract
from app.models.lesson import Lesson
from app.models.payment import Payment
from app.models.trial_booking import TrialBooking
from app.models.user import User
from app.services.pdf import generate_contract_pdf

INTAKE_TOKEN_TTL = timedelta(days=7)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contracts", tags=["contracts"])


class IntakeData(BaseModel):
    intake_token: str
    child_name: str
    child_birth_date: date
    parent_name: str
    parent_phone: str
    passport_data: str
    # amount намеренно не принимается от клиента — иначе можно подписать
    # договор на 0.01 ₽. Берём из настроек/тарифа.


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
    # Блокируем строку брони — один токен можно «погасить» только один раз,
    # даже при параллельных POST-запросах.
    result = await db.execute(
        select(TrialBooking)
        .where(TrialBooking.intake_token == data.intake_token)
        .with_for_update()
    )
    booking = result.scalar_one_or_none()
    if not booking:
        raise HTTPException(404, "Анкета не найдена или ссылка устарела")

    # Один токен — одна анкета (защита от переиспользования)
    if booking.status == "intake_done":
        raise HTTPException(410, "Эта ссылка уже была использована")

    # Срок жизни токена — 7 дней с момента создания брони
    if booking.created_at:
        created = booking.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - created > INTAKE_TOKEN_TTL:
            raise HTTPException(410, "Срок действия ссылки истёк")

    lesson_res = await db.execute(select(Lesson).where(Lesson.id == booking.lesson_id))
    trial_lesson = lesson_res.scalar_one_or_none()

    client = Client(
        lead_id=booking.lead_id,
        child_name=data.child_name,
        child_birth_date=data.child_birth_date,
        parent_name=data.parent_name,
        parent_phone=data.parent_phone,
        passport_data=data.passport_data,
        group_id=trial_lesson.group_id if trial_lesson else None,
    )
    db.add(client)
    await db.flush()
    booking.status = "intake_done"

    contract = Contract(client_id=client.id, amount=settings.default_contract_amount)
    db.add(contract)
    # Коммитим, не дожидаясь PDF: блокировка на trial_booking снимается, повторный
    # POST увидит status=intake_done и вернёт 410 раньше, чем мы успеем сгенерить
    # тяжёлый PDF.
    await db.commit()
    await db.refresh(contract)

    try:
        pdf_path = await generate_contract_pdf(client, contract)
        contract.pdf_path = pdf_path
        await db.commit()
    except Exception as e:
        logger.error("PDF generation failed for contract %s: %s", contract.id, e)
        # Договор уже создан, но PDF не сгенерирован — менеджер увидит запись
        # с pdf_path=NULL и сможет пере-сгенерировать вручную.
        raise HTTPException(500, "Не удалось сформировать PDF договора")

    logger.info("Contract created for client %s", client.id)
    return {
        "message": "Спасибо! Ваш договор готов, менеджер распечатает его к вашему приходу.",
        "contract_id": contract.id,
    }


@router.get("", response_model=List[ContractOut], summary="Список договоров")
async def list_contracts(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "manager")),
):
    result = await db.execute(select(Contract).order_by(Contract.created_at.desc()))
    return result.scalars().all()


@router.get("/{contract_id}", response_model=ContractOut, summary="Договор по ID")
async def get_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "manager")),
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
    _: User = Depends(require_role("admin", "manager")),
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
    _: User = Depends(require_role("admin", "manager")),
):
    # Блокируем договор — без этого два одновременных /sign создадут
    # два Payment-а на первый месяц.
    result = await db.execute(
        select(Contract).where(Contract.id == contract_id).with_for_update()
    )
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
