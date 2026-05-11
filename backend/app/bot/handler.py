import logging
from datetime import datetime, timedelta, timezone

from telegram import Update
from telegram.ext import Application, MessageHandler, filters

from app.config import settings

logger = logging.getLogger(__name__)

TARGET_KEYWORDS = [
    "запись", "курс", "программирование", "ребёнок", "цена",
    "урок", "пробный", "записаться", "стоимость", "занятия",
    "обучение", "школа",
]


def is_target_message(text: str) -> bool:
    text_lower = text.lower().strip()
    return any(kw in text_lower for kw in TARGET_KEYWORDS)


async def _create_lead_in_db(username: str, text: str, chat_id: str) -> int | None:
    """Create a lead directly in DB — avoids needing a JWT for internal calls."""
    try:
        from sqlalchemy import select
        from app.database import async_session_maker
        from app.models.lead import Lead
        from app.models.call_task import CallTask

        async with async_session_maker() as db:
            lead = Lead(
                name=username,
                phone="—",
                source="telegram",
                message_text=text,
                telegram_chat_id=chat_id,
                status="new",
            )
            db.add(lead)
            await db.flush()

            call_task = CallTask(
                lead_id=lead.id,
                next_call_at=datetime.now(timezone.utc) + timedelta(hours=2),
            )
            db.add(call_task)
            await db.commit()
            logger.info("Lead created from Telegram bot: id=%s name=%s", lead.id, username)
            return lead.id
    except Exception as e:
        logger.error("Failed to create lead in DB: %s", e)
        return None


async def handle_message(update: Update, context) -> None:
    msg = update.message
    if not msg or not msg.text:
        return

    text = msg.text
    chat_id = str(msg.chat_id)
    username = msg.from_user.username or msg.from_user.first_name or "Неизвестно"

    if is_target_message(text):
        await _create_lead_in_db(username, text, chat_id)

        await msg.reply_text(
            "Спасибо за обращение! Наш менеджер свяжется с вами в течение 2 часов."
        )

        manager_chat = settings.manager_telegram_chat_id
        if manager_chat:
            await context.bot.send_message(
                chat_id=manager_chat,
                text=f"🔔 Новый лид из Telegram! Имя: {username}, текст: {text[:200]}",
            )
    else:
        await msg.reply_text(
            "Спасибо за сообщение! Если вас интересует запись на курсы программирования — напишите нам."
        )


def create_bot_application() -> Application | None:
    if not settings.telegram_bot_token:
        return None
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app
