import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification

logger = logging.getLogger(__name__)


async def _send_telegram(chat_id: str, message: str) -> bool:
    """Send Telegram message. Returns False if not configured."""
    from app.config import settings
    if not settings.telegram_bot_token or not chat_id:
        logger.info("Telegram not configured, skipping: %s", message[:80])
        return False
    try:
        import httpx
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})
            return r.status_code == 200
    except Exception as e:
        logger.error("Telegram send failed: %s", e)
        return False


async def notify_manager(db: AsyncSession, message: str, recipient_id: int, chat_id: str = "") -> None:
    from app.config import settings
    target_chat = chat_id or settings.manager_telegram_chat_id
    await _send_telegram(target_chat, message)
    n = Notification(
        recipient_type="manager",
        recipient_id=recipient_id,
        channel="telegram",
        message=message,
    )
    db.add(n)


async def notify_admin(db: AsyncSession, message: str, recipient_id: int) -> None:
    from app.config import settings
    await _send_telegram(settings.admin_telegram_chat_id, message)
    n = Notification(
        recipient_type="admin",
        recipient_id=recipient_id,
        channel="telegram",
        message=message,
    )
    db.add(n)


async def notify_lead(db: AsyncSession, lead_id: int, chat_id: str, message: str) -> None:
    await _send_telegram(chat_id, message)
    n = Notification(
        recipient_type="lead",
        recipient_id=lead_id,
        channel="telegram",
        message=message,
    )
    db.add(n)
