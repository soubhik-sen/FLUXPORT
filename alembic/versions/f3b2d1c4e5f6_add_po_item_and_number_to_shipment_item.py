"""add po_item_id and po_number to shipment_item

Revision ID: f3b2d1c4e5f6
Revises: c2b7f3a1d9e4
Create Date: 2026-02-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f3b2d1c4e5f6"
down_revision: Union[str, Sequence[str], None] = "c2b7f3a1d9e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("shipment_item", sa.Column("po_item_id", sa.Integer(), nullable=True))
    op.add_column("shipment_item", sa.Column("po_number", sa.String(length=20), nullable=True))
    op.create_foreign_key(
        "fk_shipment_item_po_item_id",
        "shipment_item",
        "po_item",
        ["po_item_id"],
        ["id"],
    )

    # Backfill from schedule line -> po item -> po header
    op.execute(
        """
        UPDATE shipment_item
        SET po_item_id = po_schedule_line.po_item_id
        FROM po_schedule_line
        WHERE shipment_item.po_schedule_line_id = po_schedule_line.id
          AND shipment_item.po_item_id IS NULL
        """
    )
    op.execute(
        """
        UPDATE shipment_item
        SET po_number = po_header.po_number
        FROM po_schedule_line
        JOIN po_item ON po_item.id = po_schedule_line.po_item_id
        JOIN po_header ON po_header.id = po_item.po_header_id
        WHERE shipment_item.po_schedule_line_id = po_schedule_line.id
          AND shipment_item.po_number IS NULL
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_shipment_item_po_item_id", "shipment_item", type_="foreignkey")
    op.drop_column("shipment_item", "po_number")
    op.drop_column("shipment_item", "po_item_id")
