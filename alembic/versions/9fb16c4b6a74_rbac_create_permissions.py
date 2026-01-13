"""RBAC create permissions

Revision ID: 9fb16c4b6a74
Revises: 006ec6ce1fdc
Create Date: 2026-01-13 15:42:15.989919

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9fb16c4b6a74'
down_revision: Union[str, Sequence[str], None] = '006ec6ce1fdc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),

        sa.Column("action_key", sa.String(length=40), nullable=False),
        sa.Column("object_type", sa.String(length=10), nullable=False),

        sa.ForeignKeyConstraint(
            ["action_key"],
            ["domains.technical_key"],
            name="fk_permissions_action_key",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["object_type"],
            ["object_types.object_type"],
            name="fk_permissions_object_type",
            ondelete="RESTRICT",
        ),

        sa.UniqueConstraint("action_key", "object_type", name="uq_permissions_action_object"),
    )

    op.create_index("ix_permissions_action_key", "permissions", ["action_key"])
    op.create_index("ix_permissions_object_type", "permissions", ["object_type"])


def downgrade() -> None:
    op.drop_index("ix_permissions_object_type", table_name="permissions")
    op.drop_index("ix_permissions_action_key", table_name="permissions")
    op.drop_table("permissions")
