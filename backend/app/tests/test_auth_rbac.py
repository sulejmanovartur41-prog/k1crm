"""Тесты на разделение прав по ролям.

Раньше отсутствовали — что было прямо отмечено в код-ревью: фронт-RBAC
фиктивен, а на API ни одного теста, что teacher не может получить
доступ к /contracts или /dashboard.
"""
import pytest

from app.api.v1.auth import hash_password
from app.models.user import User


async def _login(client, db_session, role: str, login: str) -> dict:
    user = User(role=role, name=role.capitalize(), login=login, password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.commit()
    resp = await client.post("/api/v1/auth/login", data={"username": login, "password": "pass"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.asyncio
async def test_teacher_cannot_list_contracts(client, db_session):
    headers = await _login(client, db_session, "teacher", "rbac_t1")
    resp = await client.get("/api/v1/contracts", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_teacher_cannot_open_dashboard(client, db_session):
    headers = await _login(client, db_session, "teacher", "rbac_t2")
    resp = await client.get("/api/v1/payments/dashboard", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_manager_cannot_open_dashboard(client, db_session):
    headers = await _login(client, db_session, "manager", "rbac_m1")
    resp = await client.get("/api/v1/payments/dashboard", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_manager_cannot_mark_attendance(client, db_session):
    headers = await _login(client, db_session, "manager", "rbac_m2")
    # /attendance/lessons/{id}/mark — только admin/teacher
    resp = await client.post(
        "/api/v1/attendance/lessons/999/mark",
        json={"marks": []},
        headers=headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_open_dashboard(client, db_session):
    headers = await _login(client, db_session, "admin", "rbac_a1")
    resp = await client.get("/api/v1/payments/dashboard", headers=headers)
    # 200 — пустой дашборд работает; главное, что не 403
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client, db_session):
    resp = await client.get("/api/v1/contracts")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invalid_booking_status_rejected(client, db_session):
    """PATCH /schedule/bookings — статус должен быть из Literal-списка."""
    headers = await _login(client, db_session, "admin", "rbac_a2")
    resp = await client.patch(
        "/api/v1/schedule/bookings/1?status=hacker_value",
        headers=headers,
    )
    # 422 — Pydantic Literal не пропустит произвольную строку
    assert resp.status_code == 422
