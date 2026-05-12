import logging
from datetime import datetime, timedelta, timezone

from app.tasks._async_runner import run_async_task
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.payments.check_payment_for_lesson")
def check_payment_for_lesson(lesson_id: int):
    """После отметки посещаемости: проверить оплаты у присутствовавших."""
    from sqlalchemy import select
    from app.models.attendance import Attendance
    from app.models.client import Client
    from app.models.lead import Lead
    from app.models.lesson import Lesson
    from app.models.payment import Payment
    from app.services.notifications import notify_lead

    async def _run(session_maker):
        async with session_maker() as db:
            lesson_res = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
            lesson = lesson_res.scalar_one_or_none()
            if not lesson:
                return
            check_date = lesson.datetime.date()

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
                        Payment.period_from <= check_date,
                        Payment.period_to >= check_date,
                        Payment.status == "paid",
                    )
                )
                if pay_result.scalar_one_or_none():
                    continue

                client = (await db.execute(
                    select(Client).where(Client.id == a.client_id)
                )).scalar_one_or_none()
                if not client:
                    continue

                msg = (
                    f"Уважаемый {client.parent_name}, не вижу оплаты за период "
                    f"{check_date.isoformat()}. Пожалуйста, погасите задолженность."
                )

                # ВАЖНО: помечаем overdue ТОЛЬКО платёж, покрывающий дату урока.
                # Без period-фильтра pending за будущие месяцы (например, авансовый)
                # тоже становится overdue и через 48ч уходит в blocked.
                pending_res = await db.execute(
                    select(Payment).where(
                        Payment.client_id == client.id,
                        Payment.status == "pending",
                        Payment.period_from <= check_date,
                        Payment.period_to >= check_date,
                    )
                )
                for p in pending_res.scalars().all():
                    p.status = "overdue"
                    p.last_notified_at = datetime.now(timezone.utc)

                lead = (await db.execute(
                    select(Lead).where(Lead.id == client.lead_id)
                )).scalar_one_or_none()
                if lead and lead.telegram_chat_id:
                    await notify_lead(db, lead.id, lead.telegram_chat_id, msg)

                logger.info("Debt notification for client %s", client.id)
            await db.commit()

    run_async_task(_run)


@celery_app.task(name="app.tasks.payments.send_debt_reminders")
def send_debt_reminders():
    """Раз в день: повторно уведомлять должников, кому давно не писали."""
    from sqlalchemy import select
    from app.models.client import Client
    from app.models.lead import Lead
    from app.models.payment import Payment
    from app.services.notifications import notify_lead

    async def _run(session_maker):
        threshold = datetime.now(timezone.utc) - timedelta(hours=24)
        async with session_maker() as db:
            result = await db.execute(
                select(Payment).where(
                    Payment.status == "overdue",
                    (Payment.last_notified_at == None) | (Payment.last_notified_at <= threshold),
                )
            )
            for p in result.scalars().all():
                client = (await db.execute(
                    select(Client).where(Client.id == p.client_id)
                )).scalar_one_or_none()
                if client:
                    lead = (await db.execute(
                        select(Lead).where(Lead.id == client.lead_id)
                    )).scalar_one_or_none()
                    if lead and lead.telegram_chat_id:
                        await notify_lead(
                            db, lead.id, lead.telegram_chat_id,
                            f"Напоминание: задолженность {p.amount} ₽ за период "
                            f"{p.period_from.isoformat()}–{p.period_to.isoformat()}.",
                        )
                p.last_notified_at = datetime.now(timezone.utc)
                logger.info("Debt reminder sent for payment %s", p.id)
            await db.commit()

    run_async_task(_run)


@celery_app.task(name="app.tasks.payments.escalate_debt")
def escalate_debt():
    """Раз в 12 часов: эскалация долгов >48ч администратору, блокировка платежа."""
    from sqlalchemy import select
    from app.models.payment import Payment
    from app.services.notifications import notify_admin

    async def _run(session_maker):
        threshold = datetime.now(timezone.utc) - timedelta(hours=48)
        async with session_maker() as db:
            result = await db.execute(
                select(Payment).where(
                    Payment.status == "overdue",
                    # NULL = долг свежий, ещё не уведомляли — эскалацию пропускаем.
                    Payment.last_notified_at != None,
                    Payment.last_notified_at <= threshold,
                )
            )
            for p in result.scalars().all():
                p.status = "blocked"
                await notify_admin(
                    db,
                    f"🚫 Платёж #{p.id} клиента {p.client_id} заблокирован (просрочка > 48ч)",
                )
                logger.warning("Payment %s escalated to blocked", p.id)
            await db.commit()

    run_async_task(_run)


@celery_app.task(name="app.tasks.payments.send_renewal_reminders")
def send_renewal_reminders():
    """Раз в день: напомнить о продлении за 5 дней до конца периода."""
    from sqlalchemy import select
    from app.models.client import Client
    from app.models.lead import Lead
    from app.models.payment import Payment
    from app.services.notifications import notify_lead

    async def _run(session_maker):
        # Используем UTC-дату — beat работает в UTC (см. celery_app.py),
        # БД хранит даты в UTC. `date.today()` локали сервера могла бы
        # рассинхронизировать выборку.
        target_date = datetime.now(timezone.utc).date() + timedelta(days=5)
        async with session_maker() as db:
            result = await db.execute(
                select(Payment).where(Payment.period_to == target_date, Payment.status == "paid")
            )
            for p in result.scalars().all():
                client = (await db.execute(
                    select(Client).where(Client.id == p.client_id)
                )).scalar_one_or_none()
                if client:
                    lead = (await db.execute(
                        select(Lead).where(Lead.id == client.lead_id)
                    )).scalar_one_or_none()
                    if lead and lead.telegram_chat_id:
                        await notify_lead(
                            db, lead.id, lead.telegram_chat_id,
                            f"Через 5 дней заканчивается оплаченный период. "
                            f"Будем рады продлению занятий!",
                        )
                logger.info("Renewal reminder for payment %s", p.id)
            await db.commit()

    run_async_task(_run)


@celery_app.task(name="app.tasks.payments.generate_weekly_report")
def generate_weekly_report():
    """Каждый понедельник: отправка еженедельного отчёта администратору."""
    from sqlalchemy import select, func
    from app.models.client import Client
    from app.models.lead import Lead
    from app.models.payment import Payment
    from app.services.notifications import notify_admin

    async def _run(session_maker):
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        async with session_maker() as db:
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
            await notify_admin(db, report)
            await db.commit()

    run_async_task(_run)
