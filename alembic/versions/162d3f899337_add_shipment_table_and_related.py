"""add Shipment table and related

Revision ID: 162d3f899337
Revises: ca099de294fe
Create Date: 2026-01-18 15:03:55.087285

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '162d3f899337'
down_revision: Union[str, Sequence[str], None] = 'ca099de294fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Shipment Status Lookup
    op.create_table(
        'shipment_status_lookup',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('status_code', sa.String(length=20), nullable=False),
        sa.Column('status_name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('status_code')
    )

    # 2. Transport Mode Lookup
    op.create_table(
        'transport_mode_lookup',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('mode_code', sa.String(length=10), nullable=False),
        sa.Column('mode_name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mode_code')
    )

    # 3. Shipment Header
    op.create_table(
        'shipment_header',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('shipment_number', sa.String(length=30), nullable=False),
        sa.Column('status_id', sa.Integer(), nullable=False),
        sa.Column('mode_id', sa.Integer(), nullable=False),
        sa.Column('carrier_id', sa.Integer(), nullable=False),
        sa.Column('master_bill_lading', sa.String(length=50), nullable=True),
        sa.Column('estimated_departure', sa.Date(), nullable=True),
        sa.Column('estimated_arrival', sa.Date(), nullable=True),
        sa.Column('actual_arrival', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('shipment_number'),
        sa.ForeignKeyConstraint(['status_id'], ['shipment_status_lookup.id']),
        sa.ForeignKeyConstraint(['mode_id'], ['transport_mode_lookup.id']),
        sa.ForeignKeyConstraint(['carrier_id'], ['partner_master.id'])
    )

def downgrade() -> None:
    op.drop_table('shipment_header')
    op.drop_table('transport_mode_lookup')
    op.drop_table('shipment_status_lookup')
