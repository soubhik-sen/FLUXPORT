"""rbac create user_roles

Revision ID: 65af51762446
Revises: e0f06f54b015
Create Date: 2026-01-13 15:51:24.945799

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '65af51762446'
down_revision: Union[str, Sequence[str], None] = 'e0f06f54b015'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),

        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_user_roles_user",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"],
            name="fk_user_roles_role",
            ondelete="CASCADE",
        ),

        sa.UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),
    )

    op.create_index("ix_user_roles_user_role", "user_roles", ["user_id", "role_id"])


def downgrade() -> None:
    op.drop_index("ix_user_roles_user_role", table_name="user_roles")
    op.drop_table("user_roles")
