"""create_decision_history

Revision ID: 8f4c2d9a3e1b
Revises: 36be1e538243
Create Date: 2026-02-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f4c2d9a3e1b"
down_revision: Union[str, Sequence[str], None] = "36be1e538243"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "decision_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("object_type", sa.String(length=50), nullable=False),
        sa.Column("object_id", sa.String(length=50), nullable=False),
        sa.Column("table_slug", sa.String(length=60), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=True),
        sa.Column("rule_id", sa.String(length=100), nullable=True),
        sa.Column("result_summary", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="SUCCESS"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False, server_default=sa.text("'system@local'")),
        sa.Column("last_changed_by", sa.String(length=255), nullable=False, server_default=sa.text("'system@local'")),
    )
    op.create_index("ix_decision_history_object_type", "decision_history", ["object_type"])
    op.create_index("ix_decision_history_object_id", "decision_history", ["object_id"])
    op.create_index("ix_decision_history_table_slug", "decision_history", ["table_slug"])


def downgrade() -> None:
    op.drop_index("ix_decision_history_table_slug", table_name="decision_history")
    op.drop_index("ix_decision_history_object_id", table_name="decision_history")
    op.drop_index("ix_decision_history_object_type", table_name="decision_history")
    op.drop_table("decision_history")
