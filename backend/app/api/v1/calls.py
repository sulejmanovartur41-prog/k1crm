import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user, require_role
from app.config import settings
from app.database import get_db
from app.models.call_task import CallTask
from app.models.lead import Lead
from app.models.user import User
from app.services.notifications import notify_admin
from app.services.telephony import zadarma

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/calls", tags=["calls"])


class AttemptBody(BaseModel):
    result: str  # no_answer | answered
    outcome: Optional[str] = None  # enrolled | in_doubt | refused
    refusal_reason: Optional[str] = None


class CallTaskOut(BaseModel):
    id: int
    lead_id: int
    attempts: int
    escalated: bool
    completed: bool
    next_call_at: Optional[datetime]

    class Config:
        from_attributes = True


class InitiateCallBody(BaseModel):
    from_number: str
    to_number: str


@router.get("/tasks", response_model=List[CallTaskOut], summary="Задачи на звонок")
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CallTask).where(CallTask.completed == False).order_by(CallTask.next_call_at)
    )
    return result.scalars().all()


@router.get("/tasks/{task_id}", response_model=CallTaskOut, summary="Детали задачи")
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(CallTask).where(CallTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Задача не найдена")
    return task


@router.post("/tasks/{task_id}/attempt", summary="Зафиксировать попытку звонка")
async def register_attempt(
    task_id: int,
    body: AttemptBody,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "manager")),
):
    # Лочим CallTask — без этого два параллельных POST `/attempt` оба пройдут
    # проверку attempts < 3, оба инкрементнут — попытка потеряется.
    result = await db.execute(
        select(CallTask).where(CallTask.id == task_id).with_for_update()
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(404, "Задача не найдена")
    if task.completed:
        raise HTTPException(409, "Задача уже завершена")

    lead_result = await db.execute(select(Lead).where(Lead.id == task.lead_id))
    lead = lead_result.scalar_one_or_none()
    if not lead:
        raise HTTPException(404, "Лид не найден")

    now = datetime.now(timezone.utc)

    if body.result == "no_answer":
        task.attempts += 1
        lead.attempt_count = task.attempts
        lead.last_attempt_at = now

        if task.attempts >= 3:
            lead.status = "archived"
            lead.escalated = True
            task.escalated = True
            task.completed = True
            await notify_admin(
                db,
                f"⚠️ Недозвон ≥3 попыток: {lead.name}, {lead.phone}",
            )
            logger.warning("Lead %s escalated after 3 no-answer attempts", lead.id)
        else:
            task.next_call_at = now + timedelta(hours=3)
            lead.status = "calling"
            from app.tasks.calls import retry_call_task
            retry_call_task.apply_async((task.id,), countdown=3 * 3600)

    elif body.result == "answered":
        task.completed = True
        lead.last_attempt_at = now
        if body.outcome == "enrolled":
            lead.status = "enrolled"
        elif body.outcome == "in_doubt":
            lead.status = "in_doubt"
            from app.tasks.calls import follow_up_indoubt
            follow_up_indoubt.apply_async((lead.id,), countdown=48 * 3600)
        elif body.outcome == "refused":
            if not body.refusal_reason:
                raise HTTPException(422, "Необходимо указать причину отказа")
            lead.status = "refused"
            lead.refusal_reason = body.refusal_reason
        else:
            raise HTTPException(422, "Неверное значение outcome")
    else:
        raise HTTPException(422, "Неверное значение result")

    await db.commit()
    return {"status": "ok", "lead_status": lead.status, "attempts": task.attempts}


@router.post("/zadarma/initiate", summary="Инициировать звонок через Zadarma")
async def initiate_zadarma_call(
    body: InitiateCallBody,
    _: User = Depends(require_role("admin", "manager")),
):
    return await zadarma.initiate_call(body.from_number, body.to_number)


@router.post("/zadarma/webhook", summary="Webhook статуса звонка от Zadarma")
async def zadarma_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Принимает уведомление о завершении звонка от Zadarma.
    В prod-окружении обязателен ZADARMA_SECRET и валидная подпись.
    Не инкрементирует попытку — это делает только ручная `/attempt`, чтобы
    избежать race с UI.
    """
    body = await request.body()
    signature = request.headers.get("Signature", "")

    # Fail-secure: в prod webhook без секрета — отказ. Иначе любой может подделать.
    if not settings.zadarma_secret:
        if settings.environment != "dev":
            logger.error("Zadarma webhook hit, but ZADARMA_SECRET is empty in prod")
            raise HTTPException(401, "Webhook signing not configured")
    else:
        if not zadarma.verify_webhook(request.url.path, body, signature):
            logger.warning("Zadarma webhook: invalid signature")
            raise HTTPException(401, "Invalid signature")

    try:
        import json
        payload = json.loads(body) if body else {}
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON")

    logger.info("Zadarma webhook: %s", payload.get("event") or payload.get("call_status"))
    # Сохраняем call_id для последующей привязки к попытке — без
    # автоматической смены статуса лида (это делает менеджер вручную).
    return {"status": "received"}
