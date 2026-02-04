"""restore sys_number_ranges

Revision ID: e6e10a921188
Revises: ef12ab34cd56
Create Date: 2026-02-04 16:20:48.614387

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6e10a921188'
down_revision: Union[str, Sequence[str], None] = 'ef12ab34cd56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS sys_number_ranges (
            id SERIAL PRIMARY KEY,
            doc_category VARCHAR(20) NOT NULL,
            doc_type_id INTEGER NOT NULL,
            prefix VARCHAR(10) NOT NULL,
            current_value BIGINT NOT NULL DEFAULT 0,
            padding INTEGER NOT NULL DEFAULT 5,
            include_year BOOLEAN NOT NULL DEFAULT false,
            is_active BOOLEAN NOT NULL DEFAULT true,
            CONSTRAINT uix_category_type UNIQUE (doc_category, doc_type_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_number_range_lookup ON sys_number_ranges (doc_category, doc_type_id)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_number_range_lookup")
    op.execute("DROP TABLE IF EXISTS sys_number_ranges")
