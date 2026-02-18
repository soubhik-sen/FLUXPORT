"""add customer company and po customer links

Revision ID: f6c9a2d4b8e1
Revises: c9f4d8b1a2e3
Create Date: 2026-02-16 12:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f6c9a2d4b8e1"
down_revision: Union[str, None] = "c9f4d8b1a2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customer_master",
        sa.Column("company_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_customer_master_company_id_company_master",
        "customer_master",
        "company_master",
        ["company_id"],
        ["id"],
    )
    op.create_index(
        "ix_customer_master_company_id",
        "customer_master",
        ["company_id"],
        unique=False,
    )

    op.add_column(
        "po_header",
        sa.Column("customer_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_po_header_customer_id_customer_master",
        "po_header",
        "customer_master",
        ["customer_id"],
        ["id"],
    )
    op.create_index(
        "ix_po_header_customer_id",
        "po_header",
        ["customer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_po_header_customer_id", table_name="po_header")
    op.drop_constraint(
        "fk_po_header_customer_id_customer_master",
        "po_header",
        type_="foreignkey",
    )
    op.drop_column("po_header", "customer_id")

    op.drop_index("ix_customer_master_company_id", table_name="customer_master")
    op.drop_constraint(
        "fk_customer_master_company_id_company_master",
        "customer_master",
        type_="foreignkey",
    )
    op.drop_column("customer_master", "company_id")
