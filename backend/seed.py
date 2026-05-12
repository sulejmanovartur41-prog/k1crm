#!/usr/bin/env python3
"""
Seed: KiberOne CRM — реалистичные демо-данные
Объём: Medium (~40 лидов, 15 клиентов, 24 занятия, ~60 оплат)
Язык: русский
Воронка: реалистичная (~38% конверсия лидов в клиенты)
"""
import asyncio
import calendar
import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

import sys
sys.path.insert(0, "/app")

from app.api.v1.auth import hash_password
from app.models.user import User
from app.models.lead import Lead
from app.models.group import Group
from app.models.client import Client
from app.models.contract import Contract
from app.models.lesson import Lesson
from app.models.trial_booking import TrialBooking
from app.models.attendance import Attendance
from app.models.payment import Payment
from app.models.call_task import CallTask
from app.models.notification import Notification

# DATABASE_URL берётся из env — иначе seed не работает при смене порта/хоста.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://kibrone:password@postgres:5432/kibrone",
)
UTC = timezone.utc


def dt(y, m, d, h=10, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=UTC)


def month_end(year, month):
    return date(year, month, calendar.monthrange(year, month)[1])


# ─────────────────────────────────────────────
# 1. ДОПОЛНИТЕЛЬНЫЕ ПОЛЬЗОВАТЕЛИ
# ─────────────────────────────────────────────
EXTRA_USERS = [
    {"role": "manager", "name": "Елена Соколова", "login": "manager2"},
    {"role": "teacher", "name": "Дмитрий Попов",  "login": "teacher2"},
]

# ─────────────────────────────────────────────
# 2. ГРУППЫ И РАСПИСАНИЕ ЗАНЯТИЙ
# ─────────────────────────────────────────────
GROUPS = [
    {"name": "Scratch (7–9 лет)",          "level": "Scratch 7-9",  "room": "Кабинет 1", "teacher_login": "teacher",  "color": "#722ed1", "description": "Визуальное программирование для младших школьников."},
    {"name": "Python: Основы (10–13 лет)", "level": "Python 10-13", "room": "Кабинет 2", "teacher_login": "teacher",  "color": "#1677ff", "description": "Базовый синтаксис, условия, циклы, функции."},
    {"name": "Web-разработка (12–15 лет)", "level": "Web 12-15",    "room": "Кабинет 3", "teacher_login": "teacher2", "color": "#13c2c2", "description": "HTML, CSS, JavaScript, мини-проекты."},
    {"name": "Игровой дизайн (10–14 лет)", "level": "Game 10-14",   "room": "Кабинет 1", "teacher_login": "teacher2", "color": "#fa8c16", "description": "Введение в Unity и проектирование уровней."},
]

# 6 занятий на группу: 5 прошедших + 1 предстоящее
GROUP_LESSON_DATES = [
    [dt(2026,3,16,15), dt(2026,3,23,15), dt(2026,4,7,15),     dt(2026,4,21,15), dt(2026,5,5,15),  dt(2026,5,19,15)],
    [dt(2026,3,17,16), dt(2026,3,24,16), dt(2026,4,8,16),     dt(2026,4,22,16), dt(2026,5,6,16),  dt(2026,5,20,16)],
    [dt(2026,3,16,17,30), dt(2026,3,23,17,30), dt(2026,4,6,17,30), dt(2026,4,20,17,30), dt(2026,5,4,17,30), dt(2026,5,18,17,30)],
    [dt(2026,3,14,11), dt(2026,3,21,11), dt(2026,4,4,11),     dt(2026,4,18,11), dt(2026,5,2,11),  dt(2026,5,16,11)],
]

# ─────────────────────────────────────────────
# 3. ЛИДЫ (40 штук)
# ─────────────────────────────────────────────
LEADS = [
    # ── NEW (5) ──
    dict(name="Громова Вера",       phone="+79151001001", source="site",     status="new",      created=dt(2026,5,8)),
    dict(name="Тихонов Вадим",      phone="+79151001002", source="telegram", status="new",      created=dt(2026,5,9)),
    dict(name="Борисова Галина",     phone="+79151001003", source="phone",    status="new",      created=dt(2026,5,10)),
    dict(name="Крылов Евгений",      phone="+79151001004", source="site",     status="new",      created=dt(2026,5,10)),
    dict(name="Воронова Алина",      phone="+79151001005", source="referral", status="new",      created=dt(2026,5,11)),
    # ── CALLED (8) ──
    dict(name="Савельев Константин", phone="+79151001006", source="site",     status="called",   created=dt(2026,5,5),  attempts=1),
    dict(name="Пономарёва Инесса",   phone="+79151001007", source="telegram", status="called",   created=dt(2026,4,28), attempts=2),
    dict(name="Голубев Юрий",        phone="+79151001008", source="site",     status="called",   created=dt(2026,5,4),  attempts=1),
    dict(name="Ковалёва Марина",     phone="+79151001009", source="referral", status="called",   created=dt(2026,4,25), attempts=2),
    dict(name="Зайцев Николай",      phone="+79151001010", source="site",     status="called",   created=dt(2026,5,6),  attempts=1),
    dict(name="Мартынова Людмила",   phone="+79151001011", source="phone",    status="called",   created=dt(2026,4,30), attempts=2),
    dict(name="Смирнов Владимир",    phone="+79151001012", source="site",     status="called",   created=dt(2026,5,7),  attempts=1),
    dict(name="Антонова Светлана",   phone="+79151001013", source="telegram", status="called",   created=dt(2026,4,20), attempts=3, escalated=True),
    # ── IN_DOUBT (5) ──
    dict(name="Захаров Денис",       phone="+79151001014", source="site",     status="in_doubt", created=dt(2026,4,15), attempts=2),
    dict(name="Федотова Валентина",  phone="+79151001015", source="referral", status="in_doubt", created=dt(2026,4,18), attempts=2),
    dict(name="Мельников Роман",     phone="+79151001016", source="site",     status="in_doubt", created=dt(2026,4,22), attempts=1),
    dict(name="Степанова Жанна",     phone="+79151001017", source="telegram", status="in_doubt", created=dt(2026,4,10), attempts=2),
    dict(name="Никитин Пётр",        phone="+79151001018", source="phone",    status="in_doubt", created=dt(2026,4,5),  attempts=3, escalated=True),
    # ── ENROLLED (15) → станут клиентами ──
    dict(name="Иванова Мария",       phone="+79151001019", source="site",     status="enrolled", created=dt(2026,1,10), attempts=2),
    dict(name="Петров Сергей",       phone="+79151001020", source="referral", status="enrolled", created=dt(2026,1,15), attempts=1),
    dict(name="Сидорова Елена",      phone="+79151001021", source="site",     status="enrolled", created=dt(2026,1,20), attempts=2),
    dict(name="Козлова Анна",        phone="+79151001022", source="telegram", status="enrolled", created=dt(2026,2,3),  attempts=1),
    dict(name="Морозов Игорь",       phone="+79151001023", source="site",     status="enrolled", created=dt(2026,2,5),  attempts=2),
    dict(name="Новикова Оксана",     phone="+79151001024", source="referral", status="enrolled", created=dt(2026,2,10), attempts=1),
    dict(name="Волков Алексей",      phone="+79151001025", source="site",     status="enrolled", created=dt(2026,2,17), attempts=2),
    dict(name="Соловьёв Андрей",     phone="+79151001026", source="phone",    status="enrolled", created=dt(2026,2,24), attempts=1),
    dict(name="Кузнецова Татьяна",   phone="+79151001027", source="site",     status="enrolled", created=dt(2026,3,3),  attempts=2),
    dict(name="Попова Ирина",        phone="+79151001028", source="referral", status="enrolled", created=dt(2026,3,10), attempts=1),
    dict(name="Лебедева Наталья",    phone="+79151001029", source="site",     status="enrolled", created=dt(2026,3,15), attempts=2),
    dict(name="Козлов Виктор",       phone="+79151001030", source="telegram", status="enrolled", created=dt(2026,3,22), attempts=1),
    dict(name="Орлова Светлана",     phone="+79151001031", source="site",     status="enrolled", created=dt(2026,4,1),  attempts=2),
    dict(name="Макарова Людмила",    phone="+79151001032", source="referral", status="enrolled", created=dt(2026,4,8),  attempts=1),
    dict(name="Гусев Павел",         phone="+79151001033", source="site",     status="enrolled", created=dt(2026,4,28), attempts=2),
    # ── REFUSED (7) ──
    dict(name="Белов Игорь",         phone="+79151001034", source="site",     status="refused",  created=dt(2026,2,1),  attempts=2, refusal_reason="Слишком дорого"),
    dict(name="Ершова Надежда",      phone="+79151001035", source="phone",    status="refused",  created=dt(2026,2,8),  attempts=1, refusal_reason="Не подходит расписание"),
    dict(name="Суворов Геннадий",    phone="+79151001036", source="site",     status="refused",  created=dt(2026,3,1),  attempts=3, refusal_reason="Ребёнок передумал"),
    dict(name="Жукова Тамара",       phone="+79151001037", source="referral", status="refused",  created=dt(2026,3,8),  attempts=2, refusal_reason="Нашли другую школу"),
    dict(name="Фомин Артём",         phone="+79151001038", source="site",     status="refused",  created=dt(2026,3,15), attempts=2, refusal_reason="Слишком дорого"),
    dict(name="Калинина Вера",       phone="+79151001039", source="telegram", status="refused",  created=dt(2026,4,3),  attempts=1, refusal_reason="Не подходит расписание"),
    dict(name="Давыдов Семён",       phone="+79151001040", source="phone",    status="refused",  created=dt(2026,4,12), attempts=3, refusal_reason="Финансовые трудности"),
]

# ─────────────────────────────────────────────
# 4. КЛИЕНТЫ (привязаны к первым 15 enrolled)
# Поля: child_name, birth_date, passport, group_idx,
#        client_status, contract_status, join_month
# join_month: месяц начала занятий (1=янв .. 5=май 2026)
# ─────────────────────────────────────────────
CLIENT_SPECS = [
    ("Алёша Иванов",   date(2017,5,12), "4520 123456", 0, "active",   "signed",    1),
    ("Соня Петрова",   date(2014,9,3),  "4521 234567", 1, "active",   "signed",    1),
    ("Тимур Сидоров",  date(2012,7,18), "4522 345678", 2, "active",   "signed",    1),
    ("Маша Козлова",   date(2016,3,25), "4523 456789", 0, "active",   "signed",    2),
    ("Дима Морозов",   date(2013,11,7), "4524 567890", 1, "active",   "signed",    2),
    ("Катя Новикова",  date(2015,1,30), "4525 678901", 3, "active",   "signed",    2),
    ("Никита Волков",  date(2011,8,14), "4526 789012", 2, "active",   "signed",    2),
    ("Вика Соловьёва", date(2017,6,2),  "4527 890123", 0, "active",   "signed",    3),
    ("Артём Кузнецов", date(2014,12,19),"4528 901234", 1, "frozen",   "signed",    3),
    ("Лера Попова",    date(2016,4,8),  "4529 012345", 3, "active",   "signed",    3),
    ("Семён Лебедев",  date(2012,10,22),"4530 123456", 2, "inactive", "signed",    3),
    ("Миша Козлов",    date(2015,2,11), "4531 234567", 3, "active",   "signed",    4),
    ("Юля Орлова",     date(2013,7,5),  "4532 345678", 1, "active",   "signed",    4),
    ("Паша Макаров",   date(2017,9,28), "4533 456789", 0, "inactive", "generated", 4),
    ("Ваня Гусев",     date(2015,3,15), "4534 567890", 3, "active",   "generated", 5),
]

NOTIF_TEMPLATES = [
    "Добро пожаловать в КиберОдин! Договор подписан, ждём вас на занятиях.",
    "Напоминание: пробное занятие завтра в 15:00. Не забудьте взять сменную обувь.",
    "Напоминание об оплате за апрель 2026 — 5 000 ₽.",
    "Ваш ребёнок отсутствовал на занятии. Свяжитесь с менеджером для переноса.",
    "Напоминание: занятие через 2 часа. Приходите вовремя!",
    "Оплата за март получена. Спасибо!",
    "Новая тема на этой неделе: циклы и функции. Готовьтесь!",
    "Ваш договор продлён на следующий месяц.",
]


async def seed():
    engine = create_async_engine(DATABASE_URL, echo=False)
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with maker() as s:
        now_dt = datetime.now(UTC)

        # ── 1. Дополнительные пользователи ───────────────────────────
        existing_logins = {
            u.login for u in (await s.execute(select(User))).scalars().all()
        }
        for u in EXTRA_USERS:
            if u["login"] not in existing_logins:
                s.add(User(
                    role=u["role"],
                    name=u["name"],
                    login=u["login"],
                    password_hash=hash_password("password123"),
                ))
        await s.flush()

        # Получить ID нужных пользователей
        def get_user(login):
            return None  # будет перезаписано

        users_by_login = {
            u.login: u
            for u in (await s.execute(select(User))).scalars().all()
        }
        mgr  = users_by_login["manager"]
        t1   = users_by_login["teacher"]
        t2   = users_by_login["teacher2"]

        print(f"✓ Пользователей в БД: {len(users_by_login)}")

        # ── 2. Группы и занятия ───────────────────────────────────────
        teacher_map = {"teacher": t1, "teacher2": t2}
        group_objects = []
        for g in GROUPS:
            teacher = teacher_map[g["teacher_login"]]
            group = Group(
                name=g["name"],
                level=g["level"],
                teacher_id=teacher.id,
                room=g["room"],
                capacity=12,
                color=g["color"],
                status="active",
                description=g["description"],
            )
            s.add(group)
            group_objects.append(group)
        await s.flush()
        print(f"✓ Групп создано: {len(group_objects)}")

        lessons_by_group = []  # список списков объектов Lesson
        for g, group_obj, dates in zip(GROUPS, group_objects, GROUP_LESSON_DATES):
            teacher = teacher_map[g["teacher_login"]]
            group_lessons = []
            for lesson_dt in dates:
                lesson = Lesson(
                    group_id=group_obj.id,
                    teacher_id=teacher.id,
                    datetime=lesson_dt,
                    room=g["room"],
                    capacity=12,
                )
                s.add(lesson)
                group_lessons.append(lesson)
            lessons_by_group.append(group_lessons)
        await s.flush()

        total_lessons = sum(len(g) for g in lessons_by_group)
        print(f"✓ Занятий создано: {total_lessons} ({len(GROUPS)} группы × {total_lessons // len(GROUPS)})")

        # ── 3. Лиды ───────────────────────────────────────────────────
        lead_objects = []
        for lr in LEADS:
            lead = Lead(
                name=lr["name"],
                phone=lr["phone"],
                source=lr["source"],
                status=lr["status"],
                attempt_count=lr.get("attempts", 0),
                escalated=lr.get("escalated", False),
                refusal_reason=lr.get("refusal_reason"),
                created_at=lr["created"],
                updated_at=lr["created"],
            )
            s.add(lead)
            lead_objects.append(lead)
        await s.flush()

        status_counts = {}
        for lr in LEADS:
            status_counts[lr["status"]] = status_counts.get(lr["status"], 0) + 1
        print(f"✓ Лидов создано: {len(lead_objects)} "
              f"(new={status_counts.get('new',0)}, called={status_counts.get('called',0)}, "
              f"in_doubt={status_counts.get('in_doubt',0)}, enrolled={status_counts.get('enrolled',0)}, "
              f"refused={status_counts.get('refused',0)})")

        # ── 4. Задачи на звонок ───────────────────────────────────────
        for lead, lr in zip(lead_objects, LEADS):
            completed = lr["status"] in ("enrolled", "refused")
            s.add(CallTask(
                lead_id=lead.id,
                manager_id=mgr.id,
                attempts=lr.get("attempts", 0),
                escalated=lr.get("escalated", False),
                completed=completed,
                next_call_at=None if completed else dt(2026, 5, 13),
                created_at=lr["created"],
            ))
        await s.flush()
        print(f"✓ Задач на звонок: {len(lead_objects)}")

        # ── 5. Клиенты, договоры, пробные занятия ─────────────────────
        enrolled_leads = [
            lo for lo, lr in zip(lead_objects, LEADS)
            if lr["status"] == "enrolled"
        ]

        client_records = []  # (client_obj, g_idx, join_month, cl_status)

        for spec, lead in zip(CLIENT_SPECS, enrolled_leads):
            child_name, birth_date, passport, g_idx, cl_status, contr_status, join_month = spec
            join_dt = dt(2026, join_month, 15)

            client = Client(
                lead_id=lead.id,
                child_name=child_name,
                child_birth_date=birth_date,
                parent_name=lead.name,
                parent_phone=lead.phone,
                passport_data=passport,
                status=cl_status,
                group_id=group_objects[g_idx].id,
                created_at=join_dt,
            )
            s.add(client)
            await s.flush()

            signed_at = join_dt if contr_status == "signed" else None
            s.add(Contract(
                client_id=client.id,
                amount=Decimal("5000.00"),
                status=contr_status,
                signed_at=signed_at,
                created_at=join_dt,
            ))

            # Пробное занятие — первый урок группы
            trial_lesson = lessons_by_group[g_idx][0]
            s.add(TrialBooking(
                lead_id=lead.id,
                lesson_id=trial_lesson.id,
                status="attended",
                intake_token=uuid.uuid4().hex[:32],
                reminder_24h_sent=True,
                reminder_2h_sent=True,
                created_at=trial_lesson.datetime,
            ))

            client_records.append((client, g_idx, join_month, cl_status))

        await s.flush()
        print(f"✓ Клиентов: {len(client_records)}, договоров: {len(client_records)}, "
              f"пробных бронирований: {len(client_records)}")

        # ── 6. Оплаты (с февраля по май 2026) ─────────────────────────
        payment_count = 0
        methods = ["card", "cash"]

        for idx, (client, g_idx, join_month, cl_status) in enumerate(client_records):
            # Платежи с месяца вступления по май 2026
            for m in range(join_month, 6):
                p_from = date(2026, m, 1)
                p_to   = month_end(2026, m)

                if m < 5:  # прошедшие месяцы
                    if cl_status in ("inactive", "frozen") and m >= 4:
                        # просроченные для неактивных
                        status = "overdue"
                        paid_at = None
                        method  = None
                    else:
                        status  = "paid"
                        paid_at = dt(2026, m, 5, 12)
                        method  = methods[idx % 2]
                else:  # текущий месяц (май)
                    if cl_status == "active" and idx % 3 == 0:
                        # каждый третий заплатил заранее
                        status  = "paid"
                        paid_at = dt(2026, 5, 3, 10)
                        method  = methods[idx % 2]
                    elif cl_status == "active":
                        status  = "pending"
                        paid_at = None
                        method  = None
                    else:
                        status  = "overdue"
                        paid_at = None
                        method  = None

                s.add(Payment(
                    client_id=client.id,
                    amount=Decimal("5000.00"),
                    period_from=p_from,
                    period_to=p_to,
                    paid_at=paid_at,
                    status=status,
                    method=method,
                    created_at=dt(2026, m, 1),
                ))
                payment_count += 1

        await s.flush()
        print(f"✓ Оплат создано: {payment_count}")

        # ── 7. Посещаемость ───────────────────────────────────────────
        attendance_count = 0
        for client, g_idx, join_month, cl_status in client_records:
            teacher_id = t1.id if g_idx < 2 else t2.id
            for lesson in lessons_by_group[g_idx]:
                if lesson.datetime >= now_dt:
                    continue  # пропускаем предстоящие
                if lesson.datetime.month < join_month:
                    continue  # до прихода клиента

                if cl_status == "frozen":
                    present = lesson.datetime.month < 4   # перестал ходить в апреле
                elif cl_status == "inactive":
                    present = lesson.datetime.month < 3   # перестал ходить в марте
                else:
                    # ~85% посещаемость: пропускает каждое 7-е занятие
                    present = (lesson.id + client.id) % 7 != 0

                s.add(Attendance(
                    lesson_id=lesson.id,
                    client_id=client.id,
                    present=present,
                    marked_at=lesson.datetime,
                    marked_by=teacher_id,
                ))
                attendance_count += 1

        await s.flush()
        print(f"✓ Записей посещаемости: {attendance_count}")

        # ── 8. Уведомления ────────────────────────────────────────────
        for idx, (client, g_idx, join_month, cl_status) in enumerate(client_records[:10]):
            s.add(Notification(
                recipient_type="client",
                recipient_id=client.id,
                channel="telegram",
                message=NOTIF_TEMPLATES[idx % len(NOTIF_TEMPLATES)],
                sent_at=dt(2026, 4, 10 + idx % 15),
                status="sent",
            ))

        await s.commit()

    await engine.dispose()

    print("\n" + "─" * 50)
    print("✅ База данных наполнена реалистичными данными!")
    print("─" * 50)
    print(f"  Пользователи:        admin, manager, manager2, teacher, teacher2")
    print(f"  Группы:              {len(GROUPS)} (Scratch, Python, Web, Game)")
    print(f"  Занятий:             {total_lessons}")
    print(f"  Лидов:               {len(LEADS)} (воронка: new→called→in_doubt→enrolled/refused)")
    print(f"  Клиентов:            {len(CLIENT_SPECS)} (active/frozen/inactive)")
    print(f"  Оплат:               {payment_count} (paid/pending/overdue)")
    print(f"  Записей посещаемости:{attendance_count}")
    print(f"  Уведомлений:         10")


if __name__ == "__main__":
    asyncio.run(seed())
