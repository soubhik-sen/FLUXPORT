"""rbac create user_departments

Revision ID: 80afa5ba7a6e
Revises: c0495ba9c2d1
Create Date: 2026-01-13 14:44:11.924217

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80afa5ba7a6e'
down_revision: Union[str, Sequence[str], None] = 'c0495ba9c2d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_departments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("department", sa.String(length=80), nullable=False),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_departments_user",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id",
            "department",
            name="uq_user_departments_user_dept",
        ),
    )

    op.create_index(
        "ix_user_departments_user_id",
        "user_departments",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_departments_user_id", table_name="user_departments")
    op.drop_table("user_departments")
