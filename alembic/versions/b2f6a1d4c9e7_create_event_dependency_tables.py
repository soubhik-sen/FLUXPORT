"""create_event_dependency_tables

Revision ID: b2f6a1d4c9e7
Revises: 8f4c2d9a3e1b
Create Date: 2026-02-09 11:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2f6a1d4c9e7"
down_revision: Union[str, Sequence[str], None] = "8f4c2d9a3e1b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_profile",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=255), server_default=sa.text("'system@local'"), nullable=False),
        sa.Column("last_changed_by", sa.String(length=255), server_default=sa.text("'system@local'"), nullable=False),
        sa.UniqueConstraint("name", name="uq_event_profile_name"),
    )
    op.create_index("ix_event_profile_name", "event_profile", ["name"])

    op.create_table(
        "profile_event_map",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("event_code", sa.String(length=30), nullable=False),
        sa.Column("inclusion_rule_id", sa.String(length=120), nullable=True),
        sa.Column("anchor_event_code", sa.String(length=30), nullable=True),
        sa.Column("offset_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=255), server_default=sa.text("'system@local'"), nullable=False),
        sa.Column("last_changed_by", sa.String(length=255), server_default=sa.text("'system@local'"), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["event_profile.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["event_code"], ["event_lookup.event_code"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["anchor_event_code"], ["event_lookup.event_code"], ondelete="RESTRICT"),
        sa.UniqueConstraint("profile_id", "event_code", name="uq_profile_event_map_profile_event"),
    )
    op.create_index("ix_profile_event_map_profile_id", "profile_event_map", ["profile_id"])
    op.create_index("ix_profile_event_map_event_code", "profile_event_map", ["event_code"])
    op.create_index("ix_profile_event_map_anchor_event_code", "profile_event_map", ["anchor_event_code"])

    op.create_table(
        "event_instance",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("parent_id", sa.Integer(), nullable=False),
        sa.Column("po_header_id", sa.Integer(), nullable=True),
        sa.Column("shipment_header_id", sa.Integer(), nullable=True),
        sa.Column("event_code", sa.String(length=30), nullable=False),
        sa.Column("baseline_date", sa.Date(), nullable=True),
        sa.Column("planned_date", sa.Date(), nullable=True),
        sa.Column("actual_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="PLANNED"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=255), server_default=sa.text("'system@local'"), nullable=False),
        sa.Column("last_changed_by", sa.String(length=255), server_default=sa.text("'system@local'"), nullable=False),
        sa.ForeignKeyConstraint(["po_header_id"], ["po_header.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["shipment_header_id"], ["shipment_header.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["event_code"], ["event_lookup.event_code"], ondelete="RESTRICT"),
        sa.CheckConstraint("status IN ('PLANNED', 'COMPLETED', 'DELAYED')", name="ck_event_instance_status"),
        sa.CheckConstraint(
            "("
            "po_header_id IS NOT NULL AND shipment_header_id IS NULL AND parent_id = po_header_id"
            ") OR ("
            "po_header_id IS NULL AND shipment_header_id IS NOT NULL AND parent_id = shipment_header_id"
            ")",
            name="ck_event_instance_single_parent",
        ),
    )
    op.create_index("ix_event_instance_parent_id", "event_instance", ["parent_id"])
    op.create_index("ix_event_instance_po_header_id", "event_instance", ["po_header_id"])
    op.create_index("ix_event_instance_shipment_header_id", "event_instance", ["shipment_header_id"])
    op.create_index("ix_event_instance_event_code", "event_instance", ["event_code"])


def downgrade() -> None:
    op.drop_index("ix_event_instance_event_code", table_name="event_instance")
    op.drop_index("ix_event_instance_shipment_header_id", table_name="event_instance")
    op.drop_index("ix_event_instance_po_header_id", table_name="event_instance")
    op.drop_index("ix_event_instance_parent_id", table_name="event_instance")
    op.drop_table("event_instance")

    op.drop_index("ix_profile_event_map_anchor_event_code", table_name="profile_event_map")
    op.drop_index("ix_profile_event_map_event_code", table_name="profile_event_map")
    op.drop_index("ix_profile_event_map_profile_id", table_name="profile_event_map")
    op.drop_table("profile_event_map")

    op.drop_index("ix_event_profile_name", table_name="event_profile")
    op.drop_table("event_profile")

