"""create generic domains

Revision ID: 006ec6ce1fdc
Revises: 4cad93c557df
Create Date: 2026-01-13 15:37:50.365752

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006ec6ce1fdc'
down_revision: Union[str, Sequence[str], None] = '4cad93c557df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "domains",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),

        sa.Column("domain_name", sa.String(length=80), nullable=False),
        sa.Column("technical_key", sa.String(length=40), nullable=False),
        sa.Column("display_label", sa.String(length=120), nullable=True),

        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),

        sa.UniqueConstraint("domain_name", "technical_key", name="uq_domains_name_key"),
    )


def downgrade() -> None:
    op.drop_table("domains")
