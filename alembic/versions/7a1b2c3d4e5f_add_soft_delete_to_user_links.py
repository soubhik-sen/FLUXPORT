
"""add soft delete to user link tables

Revision ID: 7a1b2c3d4e5f
Revises: 6f1c2b3a4d5e
Create Date: 2026-01-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7a1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "6f1c2b3a4d5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_customer_map",
        sa.Column("deletion_indicator", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "user_partner_map",
        sa.Column("deletion_indicator", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("user_partner_map", "deletion_indicator")
    op.drop_column("user_customer_map", "deletion_indicator")
