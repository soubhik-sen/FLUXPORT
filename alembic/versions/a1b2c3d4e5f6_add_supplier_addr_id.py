"""add supplier addr_id

Revision ID: a1b2c3d4e5f6
Revises: 9f3c2e1a4b6d
Create Date: 2026-01-30 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "9f3c2e1a4b6d"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("supplier", sa.Column("addr_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_supplier_addr_id_masteraddr",
        "supplier",
        "masteraddr",
        ["addr_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_supplier_addr_id_masteraddr", "supplier", type_="foreignkey")
    op.drop_column("supplier", "addr_id")
