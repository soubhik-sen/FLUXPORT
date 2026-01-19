"""add Shipment ITEM table and related

Revision ID: 7a3f629bf2bb
Revises: 162d3f899337
Create Date: 2026-01-18 15:09:21.644631

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a3f629bf2bb'
down_revision: Union[str, Sequence[str], None] = '162d3f899337'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the Shipment Item (Packing List) table
    op.create_table(
        'shipment_item',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('shipment_header_id', sa.Integer(), nullable=False),
        sa.Column('po_item_id', sa.Integer(), nullable=False),
        
        # Logistics-specific volume/quantity
        sa.Column('shipped_qty', sa.Numeric(precision=15, scale=3), nullable=False),
        
        # Physical grouping (can link to a future container table)
        sa.Column('package_id', sa.String(length=50), nullable=True),
        sa.Column('gross_weight', sa.Numeric(precision=15, scale=3), nullable=True),
        
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['shipment_header_id'], ['shipment_header.id'], name='fk_shipment_item_header'),
        sa.ForeignKeyConstraint(['po_item_id'], ['po_item.id'], name='fk_shipment_item_po_line')
    )
    
    # Indexing for performance when querying "What is in this shipment?"
    op.create_index('ix_shipment_item_header_id', 'shipment_item', ['shipment_header_id'])

def downgrade() -> None:
    op.drop_index('ix_shipment_item_header_id', table_name='shipment_item')
    op.drop_table('shipment_item')
