"""add time to event dates and store offsets in minutes

Revision ID: f4b9c2d1e0a7
Revises: e8b7c6d5a4f3
Create Date: 2026-02-11 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f4b9c2d1e0a7"
down_revision = "e8b7c6d5a4f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "event_instance",
        "baseline_date",
        type_=sa.DateTime(),
        postgresql_using="baseline_date::timestamp",
    )
    op.alter_column(
        "event_instance",
        "planned_date",
        type_=sa.DateTime(),
        postgresql_using="planned_date::timestamp",
    )
    op.alter_column(
        "event_instance",
        "actual_date",
        type_=sa.DateTime(),
        postgresql_using="actual_date::timestamp",
    )


def downgrade() -> None:
    op.alter_column(
        "event_instance",
        "actual_date",
        type_=sa.Date(),
        postgresql_using="actual_date::date",
    )
    op.alter_column(
        "event_instance",
        "planned_date",
        type_=sa.Date(),
        postgresql_using="planned_date::date",
    )
    op.alter_column(
        "event_instance",
        "baseline_date",
        type_=sa.Date(),
        postgresql_using="baseline_date::date",
    )
