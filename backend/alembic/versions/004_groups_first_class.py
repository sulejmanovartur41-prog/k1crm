"""Первоклассная сущность Group: таблица + FK на clients/lessons + data migration.

Revision ID: 004
Revises: 003
Create Date: 2026-05-12 11:30:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Новая таблица groups.
    op.create_table(
        "groups",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("level", sa.String(50), nullable=True),
        sa.Column("teacher_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("room", sa.String(50), nullable=True),
        sa.Column("capacity", sa.Integer, nullable=False, server_default="12"),
        sa.Column("color", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name", name="uq_groups_name"),
    )
    op.create_index("ix_groups_name", "groups", ["name"])
    op.create_index("ix_groups_teacher_id", "groups", ["teacher_id"])

    # 2. Создаём Group-записи из существующих уникальных lessons.group_name.
    #    Каждая Group получает teacher_id/room/capacity из первого встретившегося
    #    урока (group_name был обязательным на Lesson, так что выборка
    #    непустая, если есть хотя бы один урок).
    op.execute("""
        INSERT INTO groups (name, teacher_id, room, capacity, status)
        SELECT DISTINCT ON (l.group_name)
               l.group_name,
               l.teacher_id,
               l.room,
               l.capacity,
               'active'
        FROM lessons l
        ORDER BY l.group_name, l.id
    """)

    # 3. Группы для клиентов, чьё group_name не совпадает ни с одним уроком —
    #    создаём "вакантные" группы (teacher_id NULL). На практике seed
    #    обычно держит consistency, но защитимся от прод-данных.
    op.execute("""
        INSERT INTO groups (name, status)
        SELECT DISTINCT c.group_name, 'active'
        FROM clients c
        WHERE c.group_name IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM groups g WHERE g.name = c.group_name)
    """)

    # 4. lessons.group_id (сначала nullable, после перенесения данных — NOT NULL).
    op.add_column("lessons", sa.Column("group_id", sa.Integer, sa.ForeignKey("groups.id"), nullable=True))
    op.execute("""
        UPDATE lessons
        SET group_id = g.id
        FROM groups g
        WHERE g.name = lessons.group_name
    """)
    op.alter_column("lessons", "group_id", nullable=False)
    op.create_index("ix_lessons_group_id", "lessons", ["group_id"])
    op.drop_column("lessons", "group_name")

    # 5. clients.group_id (всегда nullable — клиент может ждать назначения).
    op.add_column("clients", sa.Column("group_id", sa.Integer, sa.ForeignKey("groups.id"), nullable=True))
    op.execute("""
        UPDATE clients
        SET group_id = g.id
        FROM groups g
        WHERE clients.group_name IS NOT NULL
          AND g.name = clients.group_name
    """)
    op.create_index("ix_clients_group_id", "clients", ["group_id"])
    op.drop_index("ix_clients_group_name", table_name="clients")
    op.drop_column("clients", "group_name")


def downgrade() -> None:
    # Откат: возвращаем строковые group_name на основании имени группы.
    op.add_column("clients", sa.Column("group_name", sa.String(100), nullable=True))
    op.execute("""
        UPDATE clients
        SET group_name = g.name
        FROM groups g
        WHERE clients.group_id = g.id
    """)
    op.create_index("ix_clients_group_name", "clients", ["group_name"])
    op.drop_index("ix_clients_group_id", table_name="clients")
    op.drop_column("clients", "group_id")

    op.add_column("lessons", sa.Column("group_name", sa.String(100), nullable=True))
    op.execute("""
        UPDATE lessons
        SET group_name = g.name
        FROM groups g
        WHERE lessons.group_id = g.id
    """)
    op.alter_column("lessons", "group_name", nullable=False)
    op.drop_index("ix_lessons_group_id", table_name="lessons")
    op.drop_column("lessons", "group_id")

    op.drop_index("ix_groups_teacher_id", table_name="groups")
    op.drop_index("ix_groups_name", table_name="groups")
    op.drop_table("groups")
