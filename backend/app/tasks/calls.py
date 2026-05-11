import logging

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.calls.retry_call_task")
def retry_call_task(call_task_id: int):
    """Notify manager about a scheduled retry call."""
    import asyncio
    from sqlalchemy import select
    from app.database import async_session_maker
    from app.models.call_task import CallTask
    from app.models.lead import Lead

    async def _run():
        async with async_session_maker() as db:
            result = await db.execute(select(CallTask).where(CallTask.id == call_task_id))
            task = result.scalar_one_or_none()
            if not task:
                return
            lead_result = await db.execute(select(Lead).where(Lead.id == task.lead_id))
            lead = lead_result.scalar_one_or_none()
            if lead:
                from app.services.notifications import notify_manager
                await notify_manager(
                    db,
                    f"📞 Повторный звонок: {lead.name} ({lead.phone})",
                    recipient_id=task.manager_id or 0,
                )
                await db.commit()

    asyncio.run(_run())


@celery_app.task(name="app.tasks.calls.send_trial_reminder")
def send_trial_reminder(booking_id: int, hours_before: int):
    """Send trial lesson reminder to the lead."""
    import asyncio
    from sqlalchemy import select
    from app.database import async_session_maker
    from app.models.trial_booking import TrialBooking
    from app.models.lead import Lead
    from app.models.lesson import Lesson

    async def _run():
        async with async_session_maker() as db:
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
                from app.services.notifications import notify_lead
                await notify_lead(db, lead.id, lead.telegram_chat_id, msg)
            await db.commit()

    asyncio.run(_run())


@celery_app.task(name="app.tasks.calls.follow_up_indoubt")
def follow_up_indoubt(lead_id: int):
    """48h after 'in_doubt' — create a follow-up call task."""
    import asyncio
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from app.database import async_session_maker
    from app.models.call_task import CallTask

    async def _run():
        async with async_session_maker() as db:
            task = CallTask(
                lead_id=lead_id,
                next_call_at=datetime.now(timezone.utc) + timedelta(hours=48),
            )
            db.add(task)
            await db.commit()
            logger.info("Follow-up task created for lead %s", lead_id)

    asyncio.run(_run())
