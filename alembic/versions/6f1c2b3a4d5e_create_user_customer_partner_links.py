"""create user-customer and user-partner link tables

Revision ID: 6f1c2b3a4d5e
Revises: 1d2f3c4b5a6e
Create Date: 2026-01-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6f1c2b3a4d5e"
down_revision: Union[str, Sequence[str], None] = "1d2f3c4b5a6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_customer_map",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_email", sa.String(length=255), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("last_changed_by", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["user_email"], ["users.email"], name="fk_user_customer_email"),
        sa.ForeignKeyConstraint(["customer_id"], ["customer_master.id"], name="fk_user_customer_customer_id"),
        sa.UniqueConstraint("user_email", "customer_id", name="uq_user_customer"),
    )
    op.create_index("ix_user_customer_email", "user_customer_map", ["user_email"])
    op.create_index("ix_user_customer_customer_id", "user_customer_map", ["customer_id"])

    op.create_table(
        "user_partner_map",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_email", sa.String(length=255), nullable=False),
        sa.Column("partner_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("last_changed_by", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["user_email"], ["users.email"], name="fk_user_partner_email"),
        sa.ForeignKeyConstraint(["partner_id"], ["partner_master.id"], name="fk_user_partner_partner_id"),
        sa.UniqueConstraint("user_email", "partner_id", name="uq_user_partner"),
    )
    op.create_index("ix_user_partner_email", "user_partner_map", ["user_email"])
    op.create_index("ix_user_partner_partner_id", "user_partner_map", ["partner_id"])


def downgrade() -> None:
    op.drop_index("ix_user_partner_partner_id", table_name="user_partner_map")
    op.drop_index("ix_user_partner_email", table_name="user_partner_map")
    op.drop_table("user_partner_map")

    op.drop_index("ix_user_customer_customer_id", table_name="user_customer_map")
    op.drop_index("ix_user_customer_email", table_name="user_customer_map")
    op.drop_table("user_customer_map")
