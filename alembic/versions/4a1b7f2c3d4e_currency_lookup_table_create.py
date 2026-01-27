"""currency lookup table create

Revision ID: 4a1b7f2c3d4e
Revises: 3b7c1f2a9d01
Create Date: 2026-01-24 23:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4a1b7f2c3d4e"
down_revision: Union[str, Sequence[str], None] = "3b7c1f2a9d01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "currency_lookup",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("currency_code", sa.String(length=10), nullable=False),
        sa.Column("currency_name", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("currency_code"),
    )
    op.create_index("ix_currency_lookup_code", "currency_lookup", ["currency_code"])


def downgrade() -> None:
    op.drop_index("ix_currency_lookup_code", table_name="currency_lookup")
    op.drop_table("currency_lookup")
