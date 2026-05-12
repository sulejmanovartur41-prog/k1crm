"""Тест: /contracts/intake не принимает сумму от клиента.

Раньше клиент мог отправить amount=0.01 в JSON и подписать договор за копейку.
Теперь amount берётся из настроек (settings.default_contract_amount).
"""
import pytest
from sqlalchemy import select
from datetime import datetime, timezone

from app.config import settings
from app.models.lead import Lead
from app.models.lesson import Lesson
from app.models.trial_booking import TrialBooking
from app.models.contract import Contract
from app.models.user import User
from app.api.v1.auth import hash_password


@pytest.mark.asyncio
async def test_intake_ignores_client_amount(client, db_session):
    teacher = User(role="teacher", name="T", login="amt_t1", password_hash=hash_password("p"))
    db_session.add(teacher)
    await db_session.flush()

    lead = Lead(name="X", phone="+7000", source="site", status="enrolled")
    db_session.add(lead)
    await db_session.flush()

    lesson = Lesson(
        group_name="G",
        teacher_id=teacher.id,
        datetime=datetime(2030, 1, 1, 10, 0, tzinfo=timezone.utc),
        capacity=12,
    )
    db_session.add(lesson)
    await db_session.flush()

    booking = TrialBooking(lead_id=lead.id, lesson_id=lesson.id, intake_token="amount-test-tok")
    db_session.add(booking)
    await db_session.commit()

    # Пытаемся подсунуть amount=0.01 — должно быть проигнорировано.
    resp = await client.post(
        "/api/v1/contracts/intake",
        json={
            "intake_token": "amount-test-tok",
            "child_name": "Ч",
            "child_birth_date": "2019-01-01",
            "parent_name": "Р",
            "parent_phone": "+7000",
            "passport_data": "0000 000000",
            "amount": 0.01,
        },
    )
    assert resp.status_code == 200
    contract_id = resp.json()["contract_id"]

    contract = (await db_session.execute(
        select(Contract).where(Contract.id == contract_id)
    )).scalar_one()
    assert float(contract.amount) == settings.default_contract_amount
