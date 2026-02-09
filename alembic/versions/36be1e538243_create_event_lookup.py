"""create_event_lookup

Revision ID: 36be1e538243
Revises: p1q2r3s4t5u6
Create Date: 2026-02-08 22:18:02.487392

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '36be1e538243'
down_revision: Union[str, Sequence[str], None] = 'p1q2r3s4t5u6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "event_lookup",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("event_code", sa.String(length=30), nullable=False),
        sa.Column("event_name", sa.String(length=200), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False, server_default="EXPECTED"),
        sa.Column("application_object", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("event_code", name="uq_event_lookup_code"),
        sa.CheckConstraint(
            "event_type IN ('EXPECTED', 'UNEXPECTED')",
            name="ck_event_lookup_type",
        ),
    )
    op.create_index("ix_event_lookup_event_code", "event_lookup", ["event_code"])
    op.create_index(
        "ix_event_lookup_application_object",
        "event_lookup",
        ["application_object"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_event_lookup_application_object", table_name="event_lookup")
    op.drop_index("ix_event_lookup_event_code", table_name="event_lookup")
    op.drop_table("event_lookup")
