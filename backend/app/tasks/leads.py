import logging
from datetime import datetime, timedelta, timezone

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.leads.check_new_leads")
def check_new_leads():
    """Every 5 minutes: find new leads without a call task and notify manager."""
    import asyncio
    from sqlalchemy import select
    from app.database import async_session_maker
    from app.models.lead import Lead
    from app.models.call_task import CallTask

    async def _run():
        threshold = datetime.now(timezone.utc) - timedelta(minutes=10)
        async with async_session_maker() as db:
            result = await db.execute(
                select(Lead).where(
                    Lead.status == "new",
                    Lead.created_at <= threshold,
                )
            )
            leads = result.scalars().all()
            for lead in leads:
                ct_result = await db.execute(
                    select(CallTask).where(CallTask.lead_id == lead.id)
                )
                if not ct_result.scalar_one_or_none():
                    task = CallTask(
                        lead_id=lead.id,
                        next_call_at=datetime.now(timezone.utc) + timedelta(hours=2),
                    )
                    db.add(task)
                    logger.info("Auto call_task created for lead %s", lead.id)
            await db.commit()

    asyncio.run(_run())
