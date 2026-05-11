import pytest
from sqlalchemy import select

from app.models.lead import Lead
from app.models.call_task import CallTask
from app.api.v1.auth import hash_password
from app.models.user import User


@pytest.mark.asyncio
async def test_create_lead_auto_call_task(client, db_session):
    """Creating a lead must auto-create a CallTask within 2 hours."""
    # Seed a manager user for auth
    user = User(role="manager", name="Test Manager", login="tm1", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.commit()

    # Login
    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "tm1", "password": "pass"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create lead
    resp = await client.post(
        "/api/v1/leads",
        json={"name": "Иван Иванов", "phone": "+79001234567", "source": "telegram"},
        headers=headers,
    )
    assert resp.status_code == 201
    lead_id = resp.json()["id"]

    # Verify call_task was created
    result = await db_session.execute(select(CallTask).where(CallTask.lead_id == lead_id))
    task = result.scalar_one_or_none()
    assert task is not None
    assert task.next_call_at is not None


@pytest.mark.asyncio
async def test_lead_status_refused_requires_reason(client, db_session):
    """Changing status to 'refused' without a reason must return 422."""
    user = User(role="manager", name="M2", login="tm2", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.commit()

    login_resp = await client.post("/api/v1/auth/login", data={"username": "tm2", "password": "pass"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post(
        "/api/v1/leads",
        json={"name": "Пётр", "phone": "+7900", "source": "site"},
        headers=headers,
    )
    lead_id = create_resp.json()["id"]

    resp = await client.patch(
        f"/api/v1/leads/{lead_id}/status",
        json={"status": "refused"},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_three_no_answers_escalate(client, db_session):
    """After 3 no_answer attempts the lead must be archived and escalated."""
    user = User(role="manager", name="M3", login="tm3", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.commit()

    login_resp = await client.post("/api/v1/auth/login", data={"username": "tm3", "password": "pass"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_resp = await client.post(
        "/api/v1/leads",
        json={"name": "Эскалация", "phone": "+7111", "source": "phone"},
        headers=headers,
    )
    lead_id = create_resp.json()["id"]

    result = await db_session.execute(select(CallTask).where(CallTask.lead_id == lead_id))
    task = result.scalar_one_or_none()
    task_id = task.id

    for _ in range(3):
        resp = await client.post(
            f"/api/v1/calls/tasks/{task_id}/attempt",
            json={"result": "no_answer"},
            headers=headers,
        )
        assert resp.status_code == 200

    result = await db_session.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    assert lead.status == "archived"
    assert lead.escalated is True
