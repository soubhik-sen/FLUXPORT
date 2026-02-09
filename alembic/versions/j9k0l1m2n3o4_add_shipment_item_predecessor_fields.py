"""add predecessor fields to shipment_item

Revision ID: j9k0l1m2n3o4
Revises: h7a8b9c0d1e2
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "j9k0l1m2n3o4"
down_revision: Union[str, Sequence[str], None] = "h7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("shipment_item", sa.Column("predecessor_doc", sa.String(length=20), nullable=True))
    op.add_column("shipment_item", sa.Column("predecessor_item_no", sa.Integer(), nullable=True))
    op.add_column("shipment_item", sa.Column("shipment_item_number", sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE shipment_item
        SET predecessor_doc = po_number
        WHERE predecessor_doc IS NULL
        """
    )
    op.execute(
        """
        UPDATE shipment_item si
        SET predecessor_item_no = pi.item_number
        FROM po_item pi
        WHERE si.po_item_id = pi.id
          AND si.predecessor_item_no IS NULL
        """
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (PARTITION BY shipment_header_id ORDER BY id) AS rn
            FROM shipment_item
        )
        UPDATE shipment_item si
        SET shipment_item_number = ranked.rn
        FROM ranked
        WHERE si.id = ranked.id
          AND si.shipment_item_number IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("shipment_item", "shipment_item_number")
    op.drop_column("shipment_item", "predecessor_item_no")
    op.drop_column("shipment_item", "predecessor_doc")
