"""add unique constraint for po schedule number per item

Revision ID: m2n3o4p5q6r7
Revises: l1m2n3o4p5q6
Create Date: 2026-02-07

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "m2n3o4p5q6r7"
down_revision: Union[str, Sequence[str], None] = "l1m2n3o4p5q6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Normalize any existing duplicate (po_item_id, schedule_number) pairs
    # by re-numbering duplicates after current max schedule number per item.
    op.execute(
        """
        WITH max_per_item AS (
            SELECT po_item_id, COALESCE(MAX(schedule_number), 0) AS max_no
            FROM po_schedule_line
            GROUP BY po_item_id
        ),
        ranked AS (
            SELECT
                id,
                po_item_id,
                schedule_number,
                ROW_NUMBER() OVER (
                    PARTITION BY po_item_id, schedule_number
                    ORDER BY id
                ) AS dup_rank
            FROM po_schedule_line
        ),
        to_fix AS (
            SELECT
                r.id,
                r.po_item_id,
                m.max_no,
                ROW_NUMBER() OVER (
                    PARTITION BY r.po_item_id
                    ORDER BY r.schedule_number, r.id
                ) AS extra_idx
            FROM ranked r
            JOIN max_per_item m ON m.po_item_id = r.po_item_id
            WHERE r.dup_rank > 1
        )
        UPDATE po_schedule_line s
        SET schedule_number = f.max_no + f.extra_idx
        FROM to_fix f
        WHERE s.id = f.id
        """
    )

    op.create_unique_constraint(
        "uq_po_schedule_line_item_schedule",
        "po_schedule_line",
        ["po_item_id", "schedule_number"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_po_schedule_line_item_schedule",
        "po_schedule_line",
        type_="unique",
    )

