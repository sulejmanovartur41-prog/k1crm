import logging

from app.tasks._async_runner import run_async_task
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.calls.retry_call_task")
def retry_call_task(call_task_id: int):
    """Уведомить менеджера о запланированной повторной попытке звонка."""
    from sqlalchemy import select
    from app.models.call_task import CallTask
    from app.models.lead import Lead
    from app.services.notifications import notify_manager

    async def _run(session_maker):
        async with session_maker() as db:
            result = await db.execute(select(CallTask).where(CallTask.id == call_task_id))
            task = result.scalar_one_or_none()
            if not task:
                return
            lead_result = await db.execute(select(Lead).where(Lead.id == task.lead_id))
            lead = lead_result.scalar_one_or_none()
            if not lead:
                return
            await notify_manager(
                db,
                f"📞 Повторный звонок: {lead.name} ({lead.phone})",
                recipient_id=task.manager_id,
            )
            await db.commit()

    run_async_task(_run)


@celery_app.task(name="app.tasks.calls.send_trial_reminder")
def send_trial_reminder(booking_id: int, hours_before: int):
    """Напоминание о пробном уроке."""
    from sqlalchemy import select
    from app.models.lead import Lead
    from app.models.lesson import Lesson
    from app.models.trial_booking import TrialBooking
    from app.services.notifications import notify_lead

    async def _run(session_maker):
        async with session_maker() as db:
            result = await db.execute(select(TrialBooking).where(TrialBooking.id == booking_id))
            booking = result.scalar_one_or_none()
            if not booking or booking.status != "booked":
                return
            lead_result = await db.execute(select(Lead).where(Lead.id == booking.lead_id))
            lesson_result = await db.execute(select(Lesson).where(Lesson.id == booking.lesson_id))
            lead = lead_result.scalar_one_or_none()
            lesson = lesson_result.scalar_one_or_none()
            if not lead or not lesson:
                return

            time_str = lesson.datetime.strftime("%d.%m.%Y в %H:%M")
            if hours_before == 24:
                msg = f"Напоминаем, завтра в {time_str} ждём вас на пробном уроке в KiberOne!"
                booking.reminder_24h_sent = True
            else:
                msg = f"Ваш урок через 2 часа! {time_str}"
                booking.reminder_2h_sent = True

            if lead.telegram_chat_id:
                await notify_lead(db, lead.id, lead.telegram_chat_id, msg)
            await db.commit()

    run_async_task(_run)


@celery_app.task(name="app.tasks.calls.follow_up_indoubt")
def follow_up_indoubt(lead_id: int):
    """Через 48ч после статуса 'in_doubt' — создать follow-up задачу звонка."""
    from datetime import datetime, timedelta, timezone
    from app.models.call_task import CallTask

    async def _run(session_maker):
        async with session_maker() as db:
            task = CallTask(
                lead_id=lead_id,
                next_call_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
            db.add(task)
            await db.commit()
            logger.info("Follow-up task created for lead %s", lead_id)

    run_async_task(_run)
