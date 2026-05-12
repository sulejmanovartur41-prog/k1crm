"""Тесты на бизнес-правила, добавленные в третьем раунде ревью.

- Rate-limit на /auth/login
- create_lesson отвергает не-teacher
- Учитель видит только клиентов своей группы
- Дубль оплаты за тот же период → 409
"""
import pytest
from datetime import date, datetime, timezone
from sqlalchemy import select

from app.api.v1.auth import hash_password
from app.config import settings
from app.models.client import Client
from app.models.group import Group
from app.models.lead import Lead
from app.models.lesson import Lesson
from app.models.user import User


@pytest.mark.asyncio
async def test_login_rate_limited(client, db_session):
    """После N неудачных попыток с одного IP — 429."""
    limit = settings.login_rate_limit_per_5min
    # Используем несуществующего юзера — short-circuit в `if not user` пропускает
    # bcrypt-проверку (медленную) и тест укладывается в миллисекунды.
    for _ in range(limit):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "ghost", "password": "wrong"},
        )
        assert resp.status_code == 401

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "ghost", "password": "wrong"},
    )
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers


@pytest.mark.asyncio
async def test_create_lesson_rejects_non_teacher_user(client, db_session):
    """teacher_id, указывающий на admin, должен возвращать 422."""
    admin = User(role="admin", name="A", login="bl_admin", password_hash=hash_password("p"))
    manager = User(role="manager", name="M", login="bl_mgr", password_hash=hash_password("p"))
    db_session.add_all([admin, manager])
    await db_session.commit()

    login_resp = await client.post("/api/v1/auth/login", data={"username": "bl_admin", "password": "p"})
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    group = Group(name="Группа X", capacity=12)
    db_session.add(group)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/schedule/lessons",
        json={
            "group_id": group.id,
            "teacher_id": admin.id,  # admin, а не teacher
            "datetime": "2030-01-01T10:00:00+00:00",
            "capacity": 12,
        },
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_teacher_sees_only_own_group_clients(client, db_session):
    """GET /attendance/lessons/{id} возвращает только клиентов из group_id урока."""
    teacher = User(role="teacher", name="T", login="grp_t", password_hash=hash_password("p"))
    db_session.add(teacher)
    await db_session.flush()

    group_scratch = Group(name="Scratch", teacher_id=teacher.id, capacity=12)
    group_web = Group(name="Web", teacher_id=teacher.id, capacity=12)
    db_session.add_all([group_scratch, group_web])
    await db_session.flush()

    lead_a = Lead(name="A", phone="+71", source="phone", status="enrolled")
    lead_b = Lead(name="B", phone="+72", source="phone", status="enrolled")
    db_session.add_all([lead_a, lead_b])
    await db_session.flush()

    # Клиент A в группе Scratch, клиент B в группе Web
    client_a = Client(
        lead_id=lead_a.id, child_name="Аня", child_birth_date=date(2018, 1, 1),
        parent_name="A-родитель", parent_phone="+71", status="active",
        group_id=group_scratch.id,
    )
    client_b = Client(
        lead_id=lead_b.id, child_name="Боря", child_birth_date=date(2018, 1, 1),
        parent_name="B-родитель", parent_phone="+72", status="active",
        group_id=group_web.id,
    )
    db_session.add_all([client_a, client_b])
    await db_session.flush()

    lesson = Lesson(
        group_id=group_scratch.id,
        teacher_id=teacher.id,
        datetime=datetime(2030, 1, 1, 10, 0, tzinfo=timezone.utc),
        capacity=12,
    )
    db_session.add(lesson)
    await db_session.commit()

    login_resp = await client.post("/api/v1/auth/login", data={"username": "grp_t", "password": "p"})
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    resp = await client.get(f"/api/v1/attendance/lessons/{lesson.id}", headers=headers)
    assert resp.status_code == 200
    students = resp.json()
    names = [s["child_name"] for s in students]
    assert "Аня" in names
    assert "Боря" not in names


@pytest.mark.asyncio
async def test_teacher_lessons_filtered_by_teacher_id(client, db_session):
    """GET /schedule/lessons возвращает teacher-у только его уроки."""
    t1 = User(role="teacher", name="T1", login="ls_t1", password_hash=hash_password("p"))
    t2 = User(role="teacher", name="T2", login="ls_t2", password_hash=hash_password("p"))
    db_session.add_all([t1, t2])
    await db_session.flush()

    g_a = Group(name="A", teacher_id=t1.id, capacity=12)
    g_b = Group(name="B", teacher_id=t2.id, capacity=12)
    db_session.add_all([g_a, g_b])
    await db_session.flush()

    db_session.add_all([
        Lesson(group_id=g_a.id, teacher_id=t1.id, datetime=datetime(2030, 1, 1, 10, tzinfo=timezone.utc), capacity=12),
        Lesson(group_id=g_b.id, teacher_id=t2.id, datetime=datetime(2030, 1, 1, 11, tzinfo=timezone.utc), capacity=12),
    ])
    await db_session.commit()

    login_resp = await client.post("/api/v1/auth/login", data={"username": "ls_t1", "password": "p"})
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    resp = await client.get("/api/v1/schedule/lessons", headers=headers)
    assert resp.status_code == 200
    groups = [l["group_name"] for l in resp.json()]
    assert "A" in groups
    assert "B" not in groups


@pytest.mark.asyncio
async def test_duplicate_payment_period_rejected(client, db_session):
    """Две оплаты за один (client_id, period) — вторая возвращает 409."""
    mgr = User(role="manager", name="M", login="pdup_m", password_hash=hash_password("p"))
    db_session.add(mgr)
    await db_session.flush()

    lead = Lead(name="L", phone="+7", source="phone", status="enrolled")
    db_session.add(lead)
    await db_session.flush()

    c = Client(
        lead_id=lead.id, child_name="C", child_birth_date=date(2018, 1, 1),
        parent_name="P", parent_phone="+7", status="active",
    )
    db_session.add(c)
    await db_session.commit()

    login_resp = await client.post("/api/v1/auth/login", data={"username": "pdup_m", "password": "p"})
    headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    body = {
        "client_id": c.id,
        "amount": 5000.0,
        "period_from": "2026-06-01",
        "period_to": "2026-06-30",
        "method": "cash",
    }
    r1 = await client.post("/api/v1/payments", json=body, headers=headers)
    assert r1.status_code == 201

    r2 = await client.post("/api/v1/payments", json=body, headers=headers)
    assert r2.status_code == 409
