import pytest
from sqlalchemy import select
from datetime import date, datetime, timezone

from app.api.v1.auth import hash_password
from app.models.user import User
from app.models.lead import Lead
from app.models.client import Client
from app.models.lesson import Lesson
from app.models.attendance import Attendance


@pytest.mark.asyncio
async def test_mark_attendance_saves_records(client, db_session):
    """Marking attendance must save present/absent records for each student."""
    user = User(role="teacher", name="T", login="at1", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.commit()

    login_resp = await client.post("/api/v1/auth/login", data={"username": "at1", "password": "pass"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    lead = Lead(name="Л", phone="+7111222", source="phone", status="enrolled")
    db_session.add(lead)
    await db_session.flush()

    client_obj = Client(
        lead_id=lead.id,
        child_name="Ваня",
        child_birth_date=date(2018, 3, 15),
        parent_name="Ваня Вв",
        parent_phone="+7111222",
        status="active",
        group_name="Группа А",
    )
    db_session.add(client_obj)
    await db_session.flush()

    lesson = Lesson(
        group_name="Группа А",
        teacher_id=user.id,
        datetime=datetime(2026, 5, 10, 10, 0, tzinfo=timezone.utc),
        capacity=12,
    )
    db_session.add(lesson)
    await db_session.commit()

    resp = await client.post(
        f"/api/v1/attendance/lessons/{lesson.id}/mark",
        json={"marks": [{"client_id": client_obj.id, "present": True}]},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["marked"] == 1

    att_result = await db_session.execute(
        select(Attendance).where(
            Attendance.lesson_id == lesson.id,
            Attendance.client_id == client_obj.id,
        )
    )
    record = att_result.scalar_one_or_none()
    assert record is not None
    assert record.present is True


@pytest.mark.asyncio
async def test_double_mark_updates_existing(client, db_session):
    """Marking attendance twice must update the existing record, not create a duplicate."""
    user = User(role="teacher", name="T2", login="at2", password_hash=hash_password("pass"))
    db_session.add(user)
    await db_session.commit()

    login_resp = await client.post("/api/v1/auth/login", data={"username": "at2", "password": "pass"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    lead = Lead(name="Л2", phone="+7333444", source="phone", status="enrolled")
    db_session.add(lead)
    await db_session.flush()

    client_obj = Client(
        lead_id=lead.id,
        child_name="Маша",
        child_birth_date=date(2019, 7, 1),
        parent_name="Маша М",
        parent_phone="+7333444",
        status="active",
        group_name="Группа Б",
    )
    db_session.add(client_obj)
    await db_session.flush()

    lesson = Lesson(
        group_name="Группа Б",
        teacher_id=user.id,
        datetime=datetime(2026, 5, 11, 11, 0, tzinfo=timezone.utc),
        capacity=12,
    )
    db_session.add(lesson)
    await db_session.commit()

    await client.post(
        f"/api/v1/attendance/lessons/{lesson.id}/mark",
        json={"marks": [{"client_id": client_obj.id, "present": True}]},
        headers=headers,
    )
    await client.post(
        f"/api/v1/attendance/lessons/{lesson.id}/mark",
        json={"marks": [{"client_id": client_obj.id, "present": False}]},
        headers=headers,
    )

    from sqlalchemy import func
    count_result = await db_session.execute(
        select(func.count(Attendance.id)).where(
            Attendance.lesson_id == lesson.id,
            Attendance.client_id == client_obj.id,
        )
    )
    assert count_result.scalar() == 1

    att_result = await db_session.execute(
        select(Attendance).where(
            Attendance.lesson_id == lesson.id,
            Attendance.client_id == client_obj.id,
        )
    )
    record = att_result.scalar_one_or_none()
    assert record.present is False
