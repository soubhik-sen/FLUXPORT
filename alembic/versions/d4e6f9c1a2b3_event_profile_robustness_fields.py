"""event profile robustness fields

Revision ID: d4e6f9c1a2b3
Revises: c7d4e1b8a2f9
Create Date: 2026-02-10 16:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d4e6f9c1a2b3"
down_revision = "c7d4e1b8a2f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "event_profile",
        sa.Column(
            "version_id",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "event_profile",
        sa.Column(
            "profile_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "event_profile",
        sa.Column("effective_from", sa.Date(), nullable=True),
    )
    op.add_column(
        "event_profile",
        sa.Column("effective_to", sa.Date(), nullable=True),
    )
    op.add_column(
        "event_profile",
        sa.Column("timezone", sa.String(length=64), nullable=True),
    )

    op.add_column(
        "profile_event_map",
        sa.Column(
            "version_id",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "profile_event_map",
        sa.Column(
            "sequence",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    op.add_column(
        "event_instance",
        sa.Column(
            "version_id",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "event_instance",
        sa.Column("profile_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "event_instance",
        sa.Column("profile_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "event_instance",
        sa.Column("status_reason", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "event_instance",
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("'UTC'"),
        ),
    )

    op.create_foreign_key(
        "fk_event_instance_profile_id",
        "event_instance",
        "event_profile",
        ["profile_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_event_instance_parent_event",
        "event_instance",
        ["parent_id", "event_code"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_event_instance_parent_event", "event_instance", type_="unique")
    op.drop_constraint("fk_event_instance_profile_id", "event_instance", type_="foreignkey")
    op.drop_column("event_instance", "timezone")
    op.drop_column("event_instance", "status_reason")
    op.drop_column("event_instance", "profile_version")
    op.drop_column("event_instance", "profile_id")
    op.drop_column("event_instance", "version_id")
    op.drop_column("profile_event_map", "sequence")
    op.drop_column("profile_event_map", "version_id")
    op.drop_column("event_profile", "timezone")
    op.drop_column("event_profile", "effective_to")
    op.drop_column("event_profile", "effective_from")
    op.drop_column("event_profile", "profile_version")
    op.drop_column("event_profile", "version_id")
