"""Уникальность (lesson_id, client_id) в attendance; recipient_id NULL-able.

Revision ID: 002
Revises: 001
Create Date: 2026-05-11 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_attendance_lesson_client",
        "attendance",
        ["lesson_id", "client_id"],
    )
    op.alter_column(
        "notifications",
        "recipient_id",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "notifications",
        "recipient_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.drop_constraint(
        "uq_attendance_lesson_client",
        "attendance",
        type_="unique",
    )
