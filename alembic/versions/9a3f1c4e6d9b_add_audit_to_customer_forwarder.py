"""add_audit_to_customer_forwarder

Revision ID: 9a3f1c4e6d9b
Revises: 8c2b4d7f1e02
Create Date: 2026-01-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9a3f1c4e6d9b"
down_revision: Union[str, Sequence[str], None] = "8c2b4d7f1e02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customer_forwarder_map",
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
    )
    op.add_column(
        "customer_forwarder_map",
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
    )
    op.add_column("customer_forwarder_map", sa.Column("created_by", sa.String(length=255), nullable=True))
    op.add_column("customer_forwarder_map", sa.Column("last_changed_by", sa.String(length=255), nullable=True))
    op.execute(
        "UPDATE customer_forwarder_map "
        "SET created_at = COALESCE(created_at, now()), "
        "updated_at = COALESCE(updated_at, now()), "
        "created_by = COALESCE(created_by, 'system@local'), "
        "last_changed_by = COALESCE(last_changed_by, 'system@local')"
    )
    op.alter_column("customer_forwarder_map", "created_at", nullable=False)
    op.alter_column("customer_forwarder_map", "updated_at", nullable=False)
    op.alter_column("customer_forwarder_map", "created_by", nullable=False)
    op.alter_column("customer_forwarder_map", "last_changed_by", nullable=False)


def downgrade() -> None:
    op.drop_column("customer_forwarder_map", "last_changed_by")
    op.drop_column("customer_forwarder_map", "created_by")
    op.drop_column("customer_forwarder_map", "updated_at")
    op.drop_column("customer_forwarder_map", "created_at")
