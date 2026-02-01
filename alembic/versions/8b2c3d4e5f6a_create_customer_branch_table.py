
"""create customer branch table

Revision ID: 8b2c3d4e5f6a
Revises: 7a1b2c3d4e5f
Create Date: 2026-01-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8b2c3d4e5f6a"
down_revision: Union[str, Sequence[str], None] = "7a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("deletion_indicator", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["customer_id"], ["partner_master.id"], name="fk_customer_branch_customer_id"),
        sa.ForeignKeyConstraint(["branch_id"], ["partner_master.id"], name="fk_customer_branch_branch_id"),
        sa.UniqueConstraint("customer_id", "branch_id", "valid_from", name="uq_customer_map"),
        sa.CheckConstraint("customer_id <> branch_id", name="ck_customer_not_same_as_branch"),
    )
    op.create_index("ix_customer_branch_customer_id", "customer", ["customer_id"])
    op.create_index("ix_customer_branch_branch_id", "customer", ["branch_id"])


def downgrade() -> None:
    op.drop_index("ix_customer_branch_branch_id", table_name="customer")
    op.drop_index("ix_customer_branch_customer_id", table_name="customer")
    op.drop_table("customer")
