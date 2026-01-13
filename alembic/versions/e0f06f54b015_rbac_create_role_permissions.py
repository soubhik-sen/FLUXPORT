"""rbac create role_permissions

Revision ID: e0f06f54b015
Revises: 9fb16c4b6a74
Create Date: 2026-01-13 15:49:06.653931

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0f06f54b015'
down_revision: Union[str, Sequence[str], None] = '9fb16c4b6a74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),

        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.Column("role_name", sa.String(length=80), nullable=False),

        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"],
            name="fk_role_permissions_role",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"], ["permissions.id"],
            name="fk_role_permissions_permission",
            ondelete="CASCADE",
        ),

        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_perm"),
    )

    op.create_index("ix_role_permissions_role_perm", "role_permissions", ["role_id", "permission_id"])
    op.create_index("ix_role_permissions_role_name", "role_permissions", ["role_name"])


def downgrade() -> None:
    op.drop_index("ix_role_permissions_role_name", table_name="role_permissions")
    op.drop_index("ix_role_permissions_role_perm", table_name="role_permissions")
    op.drop_table("role_permissions")
