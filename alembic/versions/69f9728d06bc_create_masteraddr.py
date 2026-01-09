"""create masteraddr

Revision ID: 69f9728d06bc
Revises: d911e0d663e2
Create Date: 2026-01-09 23:34:03.794746

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69f9728d06bc'
down_revision: Union[str, Sequence[str], None] = 'd911e0d663e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "masteraddr",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),

        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=True),

        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("region", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("zip", sa.String(length=20), nullable=True),

        sa.Column("street", sa.String(length=200), nullable=True),
        sa.Column("housenumber", sa.String(length=20), nullable=True),

        sa.Column("phone1", sa.String(length=30), nullable=True),
        sa.Column("phone2", sa.String(length=30), nullable=True),
        sa.Column("emailid", sa.String(length=255), nullable=True),

        sa.Column("timezone", sa.String(length=64), nullable=True),

        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),

        sa.Column("deletion_indicator", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.UniqueConstraint("name", "type", name="uq_masteraddr_name_type"),
    )


def downgrade() -> None:
    op.drop_table("masteraddr")
