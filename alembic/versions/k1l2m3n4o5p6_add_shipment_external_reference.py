"""add external reference to shipment header

Revision ID: k1l2m3n4o5p6
Revises: j9k0l1m2n3o4
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "k1l2m3n4o5p6"
down_revision: Union[str, Sequence[str], None] = "j9k0l1m2n3o4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "shipment_header",
        sa.Column("external_reference", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("shipment_header", "external_reference")
