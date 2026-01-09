"""create forwarder

Revision ID: e4e2e550802f
Revises: ed7232b33e91
Create Date: 2026-01-10 00:03:36.439482

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4e2e550802f'
down_revision: Union[str, Sequence[str], None] = 'ed7232b33e91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "forwarder",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),

        sa.Column("forwarder_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),

        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),

        sa.Column("deletion_indicator", sa.Boolean(), nullable=False, server_default=sa.text("false")),

        sa.ForeignKeyConstraint(["forwarder_id"], ["masteraddr.id"], name="fk_forwarder_forwarderaddr"),
        sa.ForeignKeyConstraint(["branch_id"], ["masteraddr.id"], name="fk_forwarder_branchaddr"),

        sa.UniqueConstraint("forwarder_id", "branch_id", "valid_from", name="uq_forwarder_map"),
        sa.CheckConstraint("forwarder_id <> branch_id", name="ck_forwarder_not_same_as_branch"),
    )

    op.create_index("ix_forwarder_forwarder_id", "forwarder", ["forwarder_id"])
    op.create_index("ix_forwarder_branch_id", "forwarder", ["branch_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_forwarder_branch_id", table_name="forwarder")
    op.drop_index("ix_forwarder_forwarder_id", table_name="forwarder")
    op.drop_table("forwarder")
