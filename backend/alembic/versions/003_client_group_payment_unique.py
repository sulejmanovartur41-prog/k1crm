"""Group для клиентов; уникальность платежа (client_id, period_from, period_to).

Revision ID: 003
Revises: 002
Create Date: 2026-05-11 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("group_name", sa.String(100), nullable=True))
    op.create_index("ix_clients_group_name", "clients", ["group_name"])

    op.create_unique_constraint(
        "uq_payment_client_period",
        "payments",
        ["client_id", "period_from", "period_to"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_payment_client_period", "payments", type_="unique")
    op.drop_index("ix_clients_group_name", table_name="clients")
    op.drop_column("clients", "group_name")
