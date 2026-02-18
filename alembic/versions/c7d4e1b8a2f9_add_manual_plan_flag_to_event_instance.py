"""add manual plan flag to event_instance

Revision ID: c7d4e1b8a2f9
Revises: b2f6a1d4c9e7
Create Date: 2026-02-10 15:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c7d4e1b8a2f9"
down_revision = "b2f6a1d4c9e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "event_instance",
        sa.Column(
            "planned_date_manual_override",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("event_instance", "planned_date_manual_override")
