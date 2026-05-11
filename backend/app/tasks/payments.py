import logging
from datetime import datetime, timedelta, timezone, date

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.payments.check_payment_for_lesson")
def check_payment_for_lesson(lesson_id: int):
    """After attendance mark: check payments for present students."""
    import asyncio
    from sqlalchemy import select
    from app.database import async_session_maker
    from app.models.attendance import Attendance
    from app.models.payment import Payment
    from app.models.client import Client
    from app.services.notifications import notify_lead

    async def _run():
        today = date.today()
        async with async_session_maker() as db:
            att_result = await db.execute(
                select(Attendance).where(
                    Attendance.lesson_id == lesson_id,
                    Attendance.present == True,
                )
            )
            present = att_result.scalars().all()

            for a in present:
                pay_result = await db.execute(
                    select(Payment).where(
                        Payment.client_id == a.client_id,
                        Payment.period_from <= today,
                        Payment.period_to >= today,
                        Payment.status == "paid",
                    )
                )
                paid = pay_result.scalar_one_or_none()
                if not paid:
                    client_result = await db.execute(
                        select(Client).where(Client.id == a.client_id)
                    )
                    client = client_result.scalar_one_or_none()
                    if client:
                        msg = (
                            f"Уважаемый {client.parent_name}, задолженность за занятия. "
                            f"Пожалуйста, оплатите абонемент."
                        )
                        # Mark existing pending as overdue
                        overdue_result = await db.execute(
                            select(Payment).where(
                                Payment.client_id == client.id,
                                Payment.status == "pending",
                            )
                        )
                        for p in overdue_result.scalars().all():
                            p.status = "overdue"
                            p.last_notified_at = datetime.now(timezone.utc)

                        logger.info("Debt notification for client %s", client.id)
            await db.commit()

    asyncio.run(_run())


@celery_app.task(name="app.tasks.payments.send_debt_reminders")
def send_debt_reminders():
    """Daily at 9:00 — remind overdue clients."""
    import asyncio
    from sqlalchemy import select
    from app.database import async_session_maker
    from app.models.payment import Payment

    async def _run():
        threshold = datetime.now(timezone.utc) - timedelta(hours=24)
        async with async_session_maker() as db:
            result = await db.execute(
                select(Payment).where(
                    Payment.status == "overdue",
                    (Payment.last_notified_at == None) | (Payment.last_notified_at <= threshold),
                )
            )
            overdue = result.scalars().all()
            for p in overdue:
                p.last_notified_at = datetime.now(timezone.utc)
                logger.info("Debt reminder sent for payment %s", p.id)
            await db.commit()

    asyncio.run(_run())


@celery_app.task(name="app.tasks.payments.escalate_debt")
def escalate_debt():
    """Every 12h — escalate debt > 48h to admin and block access."""
    import asyncio
    from sqlalchemy import select
    from app.database import async_session_maker
    from app.models.payment import Payment

    async def _run():
        threshold = datetime.now(timezone.utc) - timedelta(hours=48)
        async with async_session_maker() as db:
            result = await db.execute(
                select(Payment).where(
                    Payment.status == "overdue",
                    Payment.last_notified_at <= threshold,
                )
            )
            for p in result.scalars().all():
                p.status = "blocked"
                logger.warning("Payment %s escalated to blocked", p.id)
            await db.commit()

    asyncio.run(_run())


@celery_app.task(name="app.tasks.payments.send_renewal_reminders")
def send_renewal_reminders():
    """Daily at 10:00 — remind clients whose subscription ends in 5 days."""
    import asyncio
    from sqlalchemy import select
    from app.database import async_session_maker
    from app.models.payment import Payment

    async def _run():
        target_date = date.today() + timedelta(days=5)
        async with async_session_maker() as db:
            result = await db.execute(
                select(Payment).where(Payment.period_to == target_date, Payment.status == "paid")
            )
            for p in result.scalars().all():
                logger.info("Renewal reminder for payment %s", p.id)
        # Telegram notification would go here

    asyncio.run(_run())


@celery_app.task(name="app.tasks.payments.generate_weekly_report")
def generate_weekly_report():
    """Every Monday at 8:00 — send weekly report to admin."""
    import asyncio
    from sqlalchemy import select, func
    from app.database import async_session_maker
    from app.models.payment import Payment
    from app.models.client import Client
    from app.models.lead import Lead

    async def _run():
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        async with async_session_maker() as db:
            revenue = await db.execute(
                select(func.sum(Payment.amount)).where(
                    Payment.status == "paid",
                    Payment.paid_at >= week_ago,
                )
            )
            new_clients = await db.execute(
                select(func.count(Client.id)).where(Client.created_at >= week_ago)
            )
            total_leads = await db.execute(select(func.count(Lead.id)).where(Lead.created_at >= week_ago))

            report = (
                f"📊 Еженедельный отчёт KiberOne\n"
                f"Выручка: {float(revenue.scalar() or 0):,.0f} ₽\n"
                f"Новых клиентов: {new_clients.scalar()}\n"
                f"Новых лидов: {total_leads.scalar()}"
            )
            logger.info("Weekly report generated: %s", report)
            # Send to admin via Telegram
            from app.services.notifications import notify_admin
            await notify_admin(db, report, recipient_id=0)
            await db.commit()

    asyncio.run(_run())
