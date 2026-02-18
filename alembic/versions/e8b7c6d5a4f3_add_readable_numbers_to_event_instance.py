"""add readable numbers to event_instance

Revision ID: e8b7c6d5a4f3
Revises: d4e6f9c1a2b3
Create Date: 2026-02-10 20:15:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e8b7c6d5a4f3"
down_revision = "d4e6f9c1a2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("event_instance", sa.Column("po_number", sa.String(length=40), nullable=True))
    op.add_column("event_instance", sa.Column("shipment_number", sa.String(length=40), nullable=True))
    op.create_index("ix_event_instance_po_number", "event_instance", ["po_number"], unique=False)
    op.create_index(
        "ix_event_instance_shipment_number",
        "event_instance",
        ["shipment_number"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_event_instance_shipment_number", table_name="event_instance")
    op.drop_index("ix_event_instance_po_number", table_name="event_instance")
    op.drop_column("event_instance", "shipment_number")
    op.drop_column("event_instance", "po_number")
