"""rbac create roles

Revision ID: 514154c4382d
Revises: 5d0ea7011e37
Create Date: 2026-01-13 15:24:47.093883

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '514154c4382d'
down_revision: Union[str, Sequence[str], None] = '5d0ea7011e37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )


def downgrade() -> None:
    op.drop_table("roles")
