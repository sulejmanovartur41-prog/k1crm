import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, require_role
from app.database import get_db
from app.models.lead import Lead
from app.models.call_task import CallTask
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["leads"])


class LeadCreate(BaseModel):
    name: str
    phone: str
    source: str
    message_text: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class LeadStatusUpdate(BaseModel):
    status: str
    refusal_reason: Optional[str] = None


class LeadOut(BaseModel):
    id: int
    name: str
    phone: str
    source: str
    status: str
    attempt_count: int
    escalated: bool
    message_text: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[LeadOut], summary="Список лидов")
async def list_leads(
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = select(Lead).order_by(Lead.created_at.desc())
    if status:
        q = q.where(Lead.status == status)
    if source:
        q = q.where(Lead.source == source)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/stats", summary="Статистика воронки лидов")
async def leads_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
    )
    stats = {row[0]: row[1] for row in result.all()}
    today = datetime.now(timezone.utc).date()
    new_today = await db.execute(
        select(func.count(Lead.id)).where(
            func.date(Lead.created_at) == today
        )
    )
    return {"by_status": stats, "new_today": new_today.scalar()}


@router.get("/{lead_id}", response_model=LeadOut, summary="Карточка лида")
async def get_lead(
    lead_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Лид не найден")
    return lead


@router.post("", response_model=LeadOut, status_code=201, summary="Создать лид")
async def create_lead(
    data: LeadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lead = Lead(
        name=data.name,
        phone=data.phone,
        source=data.source,
        message_text=data.message_text,
        telegram_chat_id=data.telegram_chat_id,
        status="new",
    )
    db.add(lead)
    await db.flush()

    # Auto-create call task in 2 hours
    call_task = CallTask(
        lead_id=lead.id,
        next_call_at=datetime.now(timezone.utc) + timedelta(hours=2),
    )
    db.add(call_task)
    await db.commit()
    await db.refresh(lead)
    logger.info("Lead created: id=%s source=%s", lead.id, lead.source)
    return lead


@router.patch("/{lead_id}/status", response_model=LeadOut, summary="Сменить статус лида")
async def update_lead_status(
    lead_id: int,
    data: LeadStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Лид не найден")

    if data.status in ("refused", "archived") and not data.refusal_reason:
        raise HTTPException(422, "Необходимо указать причину отказа/архивации")

    lead.status = data.status
    if data.refusal_reason:
        lead.refusal_reason = data.refusal_reason
    await db.commit()
    await db.refresh(lead)
    return lead
