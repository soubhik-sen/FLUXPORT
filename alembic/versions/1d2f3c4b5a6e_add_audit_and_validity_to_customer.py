"""add audit and validity to customer and address

Revision ID: 1d2f3c4b5a6e
Revises: 4c1e1bac1659
Create Date: 2026-01-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1d2f3c4b5a6e"
down_revision: Union[str, Sequence[str], None] = "4c1e1bac1659"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("masteraddr", sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True))
    op.add_column("masteraddr", sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True))
    op.add_column("masteraddr", sa.Column("created_by", sa.String(length=255), nullable=True))
    op.add_column("masteraddr", sa.Column("last_changed_by", sa.String(length=255), nullable=True))
    op.execute(
        "UPDATE masteraddr "
        "SET created_at = COALESCE(created_at, now()), "
        "updated_at = COALESCE(updated_at, now()), "
        "created_by = COALESCE(created_by, 'system@local'), "
        "last_changed_by = COALESCE(last_changed_by, 'system@local')"
    )
    op.alter_column("masteraddr", "created_at", nullable=False)
    op.alter_column("masteraddr", "updated_at", nullable=False)
    op.alter_column("masteraddr", "created_by", nullable=False)
    op.alter_column("masteraddr", "last_changed_by", nullable=False)

    op.add_column("customer_master", sa.Column("created_by", sa.String(length=255), nullable=True))
    op.add_column("customer_master", sa.Column("last_changed_by", sa.String(length=255), nullable=True))
    op.add_column(
        "customer_master",
        sa.Column("validity_to", sa.Date(), server_default=sa.text("DATE '9999-12-31'"), nullable=True),
    )
    op.execute(
        "UPDATE customer_master "
        "SET created_by = COALESCE(created_by, 'system@local'), "
        "last_changed_by = COALESCE(last_changed_by, 'system@local'), "
        "validity_to = COALESCE(validity_to, DATE '9999-12-31')"
    )
    op.alter_column("customer_master", "created_by", nullable=False)
    op.alter_column("customer_master", "last_changed_by", nullable=False)
    op.alter_column("customer_master", "validity_to", nullable=False)


def downgrade() -> None:
    op.drop_column("customer_master", "validity_to")
    op.drop_column("customer_master", "last_changed_by")
    op.drop_column("customer_master", "created_by")

    op.drop_column("masteraddr", "last_changed_by")
    op.drop_column("masteraddr", "created_by")
    op.drop_column("masteraddr", "updated_at")
    op.drop_column("masteraddr", "created_at")
