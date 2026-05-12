"""Регрессионные тесты на notify_admin / notify_manager.

До исправления `escalate_debt` падал с TypeError, потому что вызывал
`notify_admin(db, msg)` без `recipient_id`, а параметр был обязательным.
Этого никакой тест не ловил.
"""
import pytest
from sqlalchemy import select

from app.models.notification import Notification
from app.services.notifications import notify_admin, notify_manager


@pytest.mark.asyncio
async def test_notify_admin_without_recipient_id(db_session):
    """notify_admin без recipient_id — пишет в БД и не падает."""
    await notify_admin(db_session, "Тестовое сообщение для админа")
    await db_session.commit()

    res = await db_session.execute(
        select(Notification).where(Notification.recipient_type == "admin")
    )
    n = res.scalar_one_or_none()
    assert n is not None
    assert n.recipient_id is None
    assert n.message == "Тестовое сообщение для админа"


@pytest.mark.asyncio
async def test_notify_manager_without_recipient_id(db_session):
    """notify_manager без recipient_id — то же самое, общий канал менеджеров."""
    await notify_manager(db_session, "Сообщение менеджерам")
    await db_session.commit()

    res = await db_session.execute(
        select(Notification).where(Notification.recipient_type == "manager")
    )
    n = res.scalar_one_or_none()
    assert n is not None
    assert n.recipient_id is None
