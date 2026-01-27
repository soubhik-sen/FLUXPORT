"""create_customer_forwarder_map

Revision ID: 8c2b4d7f1e02
Revises: 7f3c2a9d5b6e
Create Date: 2026-01-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c2b4d7f1e02'
down_revision: Union[str, Sequence[str], None] = '7f3c2a9d5b6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_forwarder_map",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("forwarder_id", sa.Integer(), nullable=False),
        sa.Column("deletion_indicator", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["customer_id"], ["customer_master.id"], name="fk_customer_forwarder_customer_id"),
        sa.ForeignKeyConstraint(["forwarder_id"], ["partner_master.id"], name="fk_customer_forwarder_forwarder_id"),
        sa.UniqueConstraint("customer_id", "forwarder_id", name="uq_customer_forwarder"),
    )
    op.create_index("ix_customer_forwarder_customer_id", "customer_forwarder_map", ["customer_id"])
    op.create_index("ix_customer_forwarder_forwarder_id", "customer_forwarder_map", ["forwarder_id"])


def downgrade() -> None:
    op.drop_index("ix_customer_forwarder_forwarder_id", table_name="customer_forwarder_map")
    op.drop_index("ix_customer_forwarder_customer_id", table_name="customer_forwarder_map")
    op.drop_table("customer_forwarder_map")
