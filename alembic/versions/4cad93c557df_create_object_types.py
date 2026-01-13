"""create object_types

Revision ID: 4cad93c557df
Revises: 514154c4382d
Create Date: 2026-01-13 15:29:36.506901

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4cad93c557df'
down_revision: Union[str, Sequence[str], None] = '514154c4382d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "object_types",
        sa.Column("object_type", sa.String(length=10), primary_key=True),
        sa.Column("object_description", sa.String(length=255), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("object_types")
