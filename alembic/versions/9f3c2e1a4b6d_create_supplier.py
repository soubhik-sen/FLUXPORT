"""create supplier

Revision ID: 9f3c2e1a4b6d
Revises: 8b2c3d4e5f6a
Create Date: 2026-01-30 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision: str = "9f3c2e1a4b6d"
down_revision: str | None = "8b2c3d4e5f6a"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "supplier",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("deletion_indicator", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["supplier_id"], ["partner_master.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["branch_id"], ["partner_master.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("supplier_id", "branch_id", "valid_from", name="uq_supplier_map"),
        sa.CheckConstraint("supplier_id <> branch_id", name="ck_supplier_not_same_as_branch"),
    )
    op.create_index("ix_supplier_supplier_id", "supplier", ["supplier_id"])
    op.create_index("ix_supplier_branch_id", "supplier", ["branch_id"])


def downgrade() -> None:
    op.drop_index("ix_supplier_branch_id", table_name="supplier")
    op.drop_index("ix_supplier_supplier_id", table_name="supplier")
    op.drop_table("supplier")
