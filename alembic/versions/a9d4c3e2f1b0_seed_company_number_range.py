"""seed company number range

Revision ID: a9d4c3e2f1b0
Revises: f6c9a2d4b8e1
Create Date: 2026-02-18 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a9d4c3e2f1b0"
down_revision: Union[str, None] = "f6c9a2d4b8e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    existing = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM sys_number_ranges
            WHERE doc_category = :category
              AND doc_type_id = :type_id
            LIMIT 1
            """
        ),
        {"category": "COMPANY", "type_id": 1},
    ).scalar()
    if existing:
        return

    conn.execute(
        sa.text(
            """
            INSERT INTO sys_number_ranges
                (doc_category, doc_type_id, prefix, current_value, padding, include_year, is_active)
            VALUES
                (:category, :type_id, :prefix, :current_value, :padding, :include_year, :is_active)
            """
        ),
        {
            "category": "COMPANY",
            "type_id": 1,
            "prefix": "CMP-",
            "current_value": 0,
            "padding": 5,
            "include_year": False,
            "is_active": True,
        },
    )


def downgrade() -> None:
    # Data seed migration; keep downgrade as no-op to avoid deleting live counters.
    return
