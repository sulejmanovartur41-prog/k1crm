"""Тесты для /api/v1/groups: CRUD, RBAC, student membership."""
import pytest
from datetime import date
from sqlalchemy import select

from app.api.v1.auth import hash_password
from app.models.client import Client
from app.models.group import Group
from app.models.lead import Lead
from app.models.user import User


async def _login(client, login: str, password: str = "p") -> dict:
    resp = await client.post(
        "/api/v1/auth/login", data={"username": login, "password": password}
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.asyncio
async def test_admin_creates_group(client, db_session):
    admin = User(role="admin", name="A", login="gr_admin", password_hash=hash_password("p"))
    teacher = User(role="teacher", name="T", login="gr_t", password_hash=hash_password("p"))
    db_session.add_all([admin, teacher])
    await db_session.commit()
    headers = await _login(client, "gr_admin")

    resp = await client.post(
        "/api/v1/groups",
        json={
            "name": "Scratch (7–9 лет)",
            "level": "Scratch 7-9",
            "teacher_id": teacher.id,
            "room": "Кабинет 1",
            "capacity": 12,
            "color": "#722ed1",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Scratch (7–9 лет)"
    assert body["teacher_id"] == teacher.id
    assert body["status"] == "active"


@pytest.mark.asyncio
async def test_teacher_cannot_create_group(client, db_session):
    teacher = User(role="teacher", name="T", login="gr_t_create", password_hash=hash_password("p"))
    db_session.add(teacher)
    await db_session.commit()
    headers = await _login(client, "gr_t_create")

    resp = await client.post(
        "/api/v1/groups",
        json={"name": "Hack-group", "capacity": 12},
        headers=headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_duplicate_name_rejected(client, db_session):
    admin = User(role="admin", name="A", login="gr_dup", password_hash=hash_password("p"))
    db_session.add(admin)
    await db_session.commit()
    headers = await _login(client, "gr_dup")

    body = {"name": "Уникальная", "capacity": 12}
    r1 = await client.post("/api/v1/groups", json=body, headers=headers)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/groups", json=body, headers=headers)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_create_group_rejects_non_teacher_user(client, db_session):
    admin = User(role="admin", name="A", login="gr_nt", password_hash=hash_password("p"))
    manager = User(role="manager", name="M", login="gr_nt_m", password_hash=hash_password("p"))
    db_session.add_all([admin, manager])
    await db_session.commit()
    headers = await _login(client, "gr_nt")

    resp = await client.post(
        "/api/v1/groups",
        json={"name": "Wrong-teacher", "teacher_id": manager.id, "capacity": 12},
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_teacher_sees_only_own_groups(client, db_session):
    t1 = User(role="teacher", name="T1", login="gr_list_t1", password_hash=hash_password("p"))
    t2 = User(role="teacher", name="T2", login="gr_list_t2", password_hash=hash_password("p"))
    db_session.add_all([t1, t2])
    await db_session.flush()
    db_session.add_all([
        Group(name="Mine", teacher_id=t1.id, capacity=12),
        Group(name="Other", teacher_id=t2.id, capacity=12),
        Group(name="Vacant", teacher_id=None, capacity=12),
    ])
    await db_session.commit()

    headers = await _login(client, "gr_list_t1")
    resp = await client.get("/api/v1/groups", headers=headers)
    assert resp.status_code == 200
    names = [g["name"] for g in resp.json()]
    assert "Mine" in names
    assert "Other" not in names
    assert "Vacant" not in names  # учитель без своей группы её не видит


@pytest.mark.asyncio
async def test_admin_sees_all_groups(client, db_session):
    admin = User(role="admin", name="A", login="gr_all", password_hash=hash_password("p"))
    t = User(role="teacher", name="T", login="gr_all_t", password_hash=hash_password("p"))
    db_session.add_all([admin, t])
    await db_session.flush()
    db_session.add_all([
        Group(name="G1", teacher_id=t.id, capacity=12),
        Group(name="G2", teacher_id=None, capacity=12),
    ])
    await db_session.commit()

    headers = await _login(client, "gr_all")
    resp = await client.get("/api/v1/groups", headers=headers)
    assert resp.status_code == 200
    names = [g["name"] for g in resp.json()]
    assert {"G1", "G2"}.issubset(names)


@pytest.mark.asyncio
async def test_add_and_remove_student(client, db_session):
    admin = User(role="admin", name="A", login="gr_st", password_hash=hash_password("p"))
    db_session.add(admin)
    await db_session.flush()

    group = Group(name="Учеников", capacity=12)
    lead = Lead(name="L", phone="+7", source="phone", status="enrolled")
    db_session.add_all([group, lead])
    await db_session.flush()

    cl = Client(
        lead_id=lead.id, child_name="Ребёнок", child_birth_date=date(2018, 1, 1),
        parent_name="P", parent_phone="+7", status="active",
    )
    db_session.add(cl)
    await db_session.commit()

    headers = await _login(client, "gr_st")

    add_resp = await client.post(
        f"/api/v1/groups/{group.id}/students/{cl.id}", headers=headers
    )
    assert add_resp.status_code == 204

    await db_session.refresh(cl)
    assert cl.group_id == group.id

    rm_resp = await client.delete(
        f"/api/v1/groups/{group.id}/students/{cl.id}", headers=headers
    )
    assert rm_resp.status_code == 204
    await db_session.refresh(cl)
    assert cl.group_id is None


@pytest.mark.asyncio
async def test_get_group_detail_includes_students_and_lessons(client, db_session):
    admin = User(role="admin", name="A", login="gr_det", password_hash=hash_password("p"))
    teacher = User(role="teacher", name="T", login="gr_det_t", password_hash=hash_password("p"))
    db_session.add_all([admin, teacher])
    await db_session.flush()

    group = Group(name="С деталями", teacher_id=teacher.id, capacity=12)
    lead = Lead(name="L", phone="+7", source="phone", status="enrolled")
    db_session.add_all([group, lead])
    await db_session.flush()

    cl = Client(
        lead_id=lead.id, child_name="A", child_birth_date=date(2018, 1, 1),
        parent_name="P", parent_phone="+7", status="active", group_id=group.id,
    )
    db_session.add(cl)
    await db_session.commit()

    headers = await _login(client, "gr_det")
    resp = await client.get(f"/api/v1/groups/{group.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["teacher_name"] == "T"
    assert len(data["students"]) == 1
    assert data["students"][0]["child_name"] == "A"
    assert data["upcoming_lessons"] == []


@pytest.mark.asyncio
async def test_archive_via_patch(client, db_session):
    admin = User(role="admin", name="A", login="gr_arch", password_hash=hash_password("p"))
    db_session.add(admin)
    await db_session.flush()
    group = Group(name="Архив-тест", capacity=12)
    db_session.add(group)
    await db_session.commit()

    headers = await _login(client, "gr_arch")
    resp = await client.patch(
        f"/api/v1/groups/{group.id}",
        json={"status": "archived"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"

    # фильтр active не должен возвращать архив
    list_resp = await client.get("/api/v1/groups?status=active", headers=headers)
    names = [g["name"] for g in list_resp.json()]
    assert "Архив-тест" not in names
    list_resp = await client.get("/api/v1/groups?status=archived", headers=headers)
    names = [g["name"] for g in list_resp.json()]
    assert "Архив-тест" in names
