import pytest
from sqlalchemy import select
from datetime import date

from app.api.v1.auth import hash_password
from app.models.user import User
from app.models.lead import Lead
from app.models.client import Client
from app.models.payment import Payment


@pytest.mark.asyncio
async def test_create_payment(client, db_session):
    """Creating a payment must set status=paid and record paid_at."""
    user = User(role="manager", name="M", login="pm1", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.commit()

    login_resp = await client.post("/api/v1/auth/login", data={"username": "pm1", "password": "pass"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    lead = Lead(name="Л", phone="+7555666", source="phone", status="enrolled")
    db_session.add(lead)
    await db_session.flush()

    client_obj = Client(
        lead_id=lead.id,
        child_name="Саша",
        child_birth_date=date(2017, 9, 1),
        parent_name="Саша С",
        parent_phone="+7555666",
        status="active",
    )
    db_session.add(client_obj)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/payments",
        json={
            "client_id": client_obj.id,
            "amount": 5000.0,
            "period_from": "2026-05-01",
            "period_to": "2026-05-31",
            "method": "cash",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "paid"
    assert data["paid_at"] is not None


@pytest.mark.asyncio
async def test_overdue_list(client, db_session):
    """Overdue endpoint must return payments with status pending or overdue."""
    user = User(role="manager", name="M2", login="pm2", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.commit()

    login_resp = await client.post("/api/v1/auth/login", data={"username": "pm2", "password": "pass"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    lead = Lead(name="Д", phone="+7777888", source="phone", status="enrolled")
    db_session.add(lead)
    await db_session.flush()

    client_obj = Client(
        lead_id=lead.id,
        child_name="Дима",
        child_birth_date=date(2016, 1, 1),
        parent_name="Дима Д",
        parent_phone="+7777888",
        status="active",
    )
    db_session.add(client_obj)
    await db_session.flush()

    payment = Payment(
        client_id=client_obj.id,
        amount=5000.0,
        period_from=date(2026, 4, 1),
        period_to=date(2026, 4, 30),
        status="overdue",
    )
    db_session.add(payment)
    await db_session.commit()

    resp = await client.get("/api/v1/payments/overdue", headers=headers)
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()]
    assert payment.id in ids


@pytest.mark.asyncio
async def test_dashboard_returns_required_fields(client, db_session):
    """Dashboard must return revenue, funnel, weekly_revenue, attendance_by_group."""
    user = User(role="admin", name="A", login="pm3", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.commit()

    login_resp = await client.post("/api/v1/auth/login", data={"username": "pm3", "password": "pass"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/v1/payments/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "revenue" in data
    assert "funnel" in data
    assert "weekly_revenue" in data
    assert "attendance_by_group" in data
    assert "active_clients" in data
    assert "overdue_count" in data
    assert "lead_conversion" in data
