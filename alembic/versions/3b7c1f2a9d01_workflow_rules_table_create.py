"""workflow rules table create

Revision ID: 3b7c1f2a9d01
Revises: 22a95c9bdca1
Create Date: 2026-01-24 22:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3b7c1f2a9d01"
down_revision: Union[str, Sequence[str], None] = "22a95c9bdca1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sys_workflow_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("doc_category", sa.String(length=20), nullable=False),
        sa.Column("doc_type_id", sa.Integer(), nullable=False),
        sa.Column("state_code", sa.String(length=30), nullable=False),
        sa.Column("action_key", sa.String(length=60), nullable=False),
        sa.Column("required_role_id", sa.Integer(), nullable=False),
        sa.Column("is_blocking", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(
            ["doc_type_id"],
            ["document_type_lookup.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["required_role_id"],
            ["roles.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "doc_category",
            "doc_type_id",
            "state_code",
            "action_key",
            name="uq_workflow_rules_doc_type_state_action",
        ),
    )
    op.create_index(
        "ix_workflow_rules_lookup",
        "sys_workflow_rules",
        ["doc_category", "doc_type_id", "state_code"],
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_rules_lookup", table_name="sys_workflow_rules")
    op.drop_table("sys_workflow_rules")
