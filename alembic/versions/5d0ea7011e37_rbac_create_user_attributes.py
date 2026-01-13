"""rbac create user_attributes

Revision ID: 5d0ea7011e37
Revises: 80afa5ba7a6e
Create Date: 2026-01-13 15:21:56.568407

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5d0ea7011e37'
down_revision: Union[str, Sequence[str], None] = '80afa5ba7a6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_attributes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_attributes_user",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id",
            "key",
            name="uq_user_attributes_user_key",
        ),
    )

    op.create_index(
        "ix_user_attributes_user_id",
        "user_attributes",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_attributes_user_id", table_name="user_attributes")
    op.drop_table("user_attributes")
