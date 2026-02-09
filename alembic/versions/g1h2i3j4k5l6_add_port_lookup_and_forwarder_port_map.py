"""add port lookup and forwarder port map

Revision ID: g1h2i3j4k5l6
Revises: f3b2d1c4e5f6
Create Date: 2026-02-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, Sequence[str], None] = "f3b2d1c4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "port_lookup",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("port_code", sa.String(length=20), nullable=False),
        sa.Column("port_name", sa.String(length=150), nullable=False),
        sa.Column("country", sa.String(length=80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_port_lookup_port_code"), "port_lookup", ["port_code"], unique=True)

    op.create_table(
        "forwarder_port_map",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("forwarder_id", sa.Integer(), nullable=False),
        sa.Column("port_id", sa.Integer(), nullable=False),
        sa.Column("deletion_indicator", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("last_changed_by", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["forwarder_id"], ["partner_master.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["port_id"], ["port_lookup.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("forwarder_id", "port_id", name="uq_forwarder_port"),
    )
    op.create_index(op.f("ix_forwarder_port_map_forwarder_id"), "forwarder_port_map", ["forwarder_id"], unique=False)
    op.create_index(op.f("ix_forwarder_port_map_port_id"), "forwarder_port_map", ["port_id"], unique=False)

    op.add_column("shipment_header", sa.Column("pol_port_id", sa.Integer(), nullable=True))
    op.add_column("shipment_header", sa.Column("pod_port_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_shipment_header_pol_port",
        "shipment_header",
        "port_lookup",
        ["pol_port_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_shipment_header_pod_port",
        "shipment_header",
        "port_lookup",
        ["pod_port_id"],
        ["id"],
    )
    op.create_index(op.f("ix_shipment_header_pol_port_id"), "shipment_header", ["pol_port_id"], unique=False)
    op.create_index(op.f("ix_shipment_header_pod_port_id"), "shipment_header", ["pod_port_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_shipment_header_pod_port_id"), table_name="shipment_header")
    op.drop_index(op.f("ix_shipment_header_pol_port_id"), table_name="shipment_header")
    op.drop_constraint("fk_shipment_header_pod_port", "shipment_header", type_="foreignkey")
    op.drop_constraint("fk_shipment_header_pol_port", "shipment_header", type_="foreignkey")
    op.drop_column("shipment_header", "pod_port_id")
    op.drop_column("shipment_header", "pol_port_id")

    op.drop_index(op.f("ix_forwarder_port_map_port_id"), table_name="forwarder_port_map")
    op.drop_index(op.f("ix_forwarder_port_map_forwarder_id"), table_name="forwarder_port_map")
    op.drop_table("forwarder_port_map")

    op.drop_index(op.f("ix_port_lookup_port_code"), table_name="port_lookup")
    op.drop_table("port_lookup")
