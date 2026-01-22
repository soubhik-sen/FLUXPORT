"""Add po_schedule_line and update shipment_item link

Revision ID: a56828451eaa
Revises: 300576264ed4
Create Date: 2026-01-21 17:18:25.654241

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a56828451eaa'
down_revision: Union[str, Sequence[str], None] = '300576264ed4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from alembic import op
import sqlalchemy as sa

def upgrade():
    # --- STEP 1: Create the new Schedule Line Table ---
    op.create_table(
        'po_schedule_line',
        sa.Column('id', sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column('po_item_id', sa.Integer(), sa.ForeignKey('po_item.id'), nullable=False),
        sa.Column('shipment_header_id', sa.Integer(), sa.ForeignKey('shipment_header.id'), nullable=True),
        sa.Column('schedule_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('quantity', sa.Numeric(precision=15, scale=3), nullable=False),
        sa.Column('received_qty', sa.Numeric(precision=15, scale=3), server_default='0.000'),
        sa.Column('delivery_date', sa.Date(), nullable=False)
    )

    # --- STEP 2: Data Migration (Preserve Existing Commercial Links) ---
    # Create a default schedule line for every existing PO Item using raw SQL
    op.execute("""
        INSERT INTO po_schedule_line (po_item_id, quantity, delivery_date, schedule_number)
        SELECT id, quantity, CURRENT_DATE, 1 FROM po_item
    """)

    # --- STEP 3: Update Shipment Item Table ---
    # 1. Add the new column as nullable first
    op.add_column('shipment_item', sa.Column('po_schedule_line_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_shipment_item_schedule', 'shipment_item', 'po_schedule_line', ['po_schedule_line_id'], ['id'])

    # 2. Map existing ShipmentItems to the newly created ScheduleLines
    # Logic: Match them where the ScheduleLine's parent POItem matches the ShipmentItem's parent POItem
    op.execute("""
        UPDATE shipment_item
        SET po_schedule_line_id = (
            SELECT id FROM po_schedule_line 
            WHERE po_schedule_line.po_item_id = shipment_item.po_item_id
            LIMIT 1
        )
    """)

    # 3. Add split_count to po_item
    op.add_column('po_item', sa.Column('split_count', sa.Integer(), nullable=False, server_default='1'))

    # --- STEP 4: Cleanup & Constraints ---
    # Now that data is migrated, make the link mandatory
    op.alter_column('shipment_item', 'po_schedule_line_id', nullable=False)
    # Drop the old direct link to PO Item
    op.drop_constraint('fk_shipment_item_po_item', 'shipment_item', type_='foreignkey') # Name may vary based on your DB
    op.drop_column('shipment_item', 'po_item_id')

def downgrade():
    # Reverse logic: Re-add po_item_id to shipment_item and drop new table
    op.add_column('shipment_item', sa.Column('po_item_id', sa.Integer(), sa.ForeignKey('po_item.id'), nullable=True))
    op.execute("""
        UPDATE shipment_item
        SET po_item_id = (
            SELECT po_item_id FROM po_schedule_line 
            WHERE po_schedule_line.id = shipment_item.po_schedule_line_id
        )
    """)
    op.drop_column('po_item', 'split_count')
    op.drop_table('po_schedule_line')
