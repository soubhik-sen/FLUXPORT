"""backfill schedule line shipment header link

Revision ID: l1m2n3o4p5q6
Revises: k1l2m3n4o5p6
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "l1m2n3o4p5q6"
down_revision: Union[str, Sequence[str], None] = "k1l2m3n4o5p6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE po_schedule_line s
        SET shipment_header_id = si.shipment_header_id
        FROM shipment_item si
        WHERE si.po_schedule_line_id = s.id
          AND s.shipment_header_id IS NULL
        """
    )


def downgrade() -> None:
    # No safe downgrade for backfill.
    pass
