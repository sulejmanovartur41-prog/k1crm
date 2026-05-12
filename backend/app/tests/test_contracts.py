import pytest
from sqlalchemy import select

from app.api.v1.auth import hash_password
from app.models.user import User
from app.models.lead import Lead
from app.models.group import Group
from app.models.lesson import Lesson
from app.models.trial_booking import TrialBooking
from app.models.client import Client
from app.models.contract import Contract
from app.models.payment import Payment
from datetime import date, datetime, timezone


@pytest.mark.asyncio
async def test_contract_intake_creates_client_and_contract(client, db_session):
    """Submitting intake form must create a Client and Contract."""
    user = User(role="manager", name="M", login="cm1", password_hash=hash_password("pass"))
    teacher = User(role="teacher", name="T", login="ct1", password_hash=hash_password("pass"))
    db_session.add_all([user, teacher])
    await db_session.commit()

    lead = Lead(name="Анна", phone="+79001111111", source="site", status="enrolled")
    group = Group(name="Группа 1", teacher_id=teacher.id, capacity=12)
    db_session.add_all([lead, group])
    await db_session.flush()

    lesson = Lesson(
        group_id=group.id,
        teacher_id=teacher.id,
        datetime=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
        capacity=12,
    )
    db_session.add(lesson)
    await db_session.flush()

    booking = TrialBooking(lead_id=lead.id, lesson_id=lesson.id, intake_token="test-token-abc123")
    db_session.add(booking)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/contracts/intake",
        json={
            "intake_token": "test-token-abc123",
            "child_name": "Петя",
            "child_birth_date": "2018-05-10",
            "parent_name": "Анна Иванова",
            "parent_phone": "+79001111111",
            "passport_data": "1234 567890",
            "amount": 5000.0,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "contract_id" in data

    contract_result = await db_session.execute(select(Contract).where(Contract.id == data["contract_id"]))
    contract = contract_result.scalar_one_or_none()
    assert contract is not None
    assert float(contract.amount) == 5000.0


@pytest.mark.asyncio
async def test_contract_sign_activates_client_and_creates_payment(client, db_session):
    """Signing a contract must set client.status=active and create a pending payment."""
    login_user = User(role="manager", name="M2", login="cm2", password_hash=hash_password("pass"))
    db_session.add(login_user)
    await db_session.commit()

    login_resp = await client.post("/api/v1/auth/login", data={"username": "cm2", "password": "pass"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    lead2 = Lead(name="Борис", phone="+7900222", source="phone", status="enrolled")
    db_session.add(lead2)
    await db_session.flush()

    client_obj = Client(
        lead_id=lead2.id,
        child_name="Боря",
        child_birth_date=date(2019, 1, 1),
        parent_name="Борис Петров",
        parent_phone="+7900222",
        status="inactive",
    )
    db_session.add(client_obj)
    await db_session.flush()

    contract = Contract(client_id=client_obj.id, amount=5000.0, status="generated")
    db_session.add(contract)
    await db_session.commit()

    resp = await client.post(f"/api/v1/contracts/{contract.id}/sign", headers=headers)
    assert resp.status_code == 200

    await db_session.refresh(client_obj)
    assert client_obj.status == "active"

    pay_result = await db_session.execute(
        select(Payment).where(Payment.client_id == client_obj.id)
    )
    payment = pay_result.scalar_one_or_none()
    assert payment is not None
    assert payment.status == "pending"


@pytest.mark.asyncio
async def test_contract_invalid_token_returns_404(client, db_session):
    """Intake with non-existent token must return 404."""
    resp = await client.post(
        "/api/v1/contracts/intake",
        json={
            "intake_token": "nonexistent-token",
            "child_name": "Х",
            "child_birth_date": "2019-01-01",
            "parent_name": "Х Х",
            "parent_phone": "+7900",
            "passport_data": "0000 000000",
        },
    )
    assert resp.status_code == 404
