from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "kibrone",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.leads",
        "app.tasks.calls",
        "app.tasks.payments",
    ],
)

celery_app.conf.beat_schedule = {
    "check-new-leads": {
        "task": "app.tasks.leads.check_new_leads",
        "schedule": crontab(minute="*/5"),
    },
    "debt-reminders": {
        "task": "app.tasks.payments.send_debt_reminders",
        "schedule": crontab(hour=9, minute=0),
    },
    "escalate-debt": {
        "task": "app.tasks.payments.escalate_debt",
        "schedule": crontab(hour="*/12"),
    },
    "renewal-reminders": {
        "task": "app.tasks.payments.send_renewal_reminders",
        "schedule": crontab(hour=10, minute=0),
    },
    "weekly-report": {
        "task": "app.tasks.payments.generate_weekly_report",
        "schedule": crontab(hour=8, minute=0, day_of_week=1),
    },
}

celery_app.conf.timezone = "Europe/Moscow"
