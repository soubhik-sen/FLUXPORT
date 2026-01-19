"""add text management

Revision ID: 300576264ed4
Revises: 1aa5e943d2e7
Create Date: 2026-01-18 19:00:23.218439

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '300576264ed4'
down_revision: Union[str, Sequence[str], None] = '1aa5e943d2e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    # 1. Create Text Type Lookup
    op.create_table(
        'text_type_lookup',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('text_type_code', sa.String(length=20), nullable=False),
        sa.Column('text_type_name', sa.String(length=100), nullable=False),
        sa.Column('is_external', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('text_type_code')
    )

    # 2. Create Text Master Table
    op.create_table(
        'text_master',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('type_id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('po_header_id', sa.Integer(), nullable=True),
        sa.Column('shipment_id', sa.Integer(), nullable=True),
        sa.Column('partner_id', sa.Integer(), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['type_id'], ['text_type_lookup.id']),
        sa.ForeignKeyConstraint(['po_header_id'], ['po_header.id']),
        sa.ForeignKeyConstraint(['shipment_id'], ['shipment_header.id']),
        sa.ForeignKeyConstraint(['partner_id'], ['partner_master.id']),
        sa.ForeignKeyConstraint(['product_id'], ['product_master.id'])
    )

def downgrade() -> None:
    op.drop_table('text_master')
    op.drop_table('text_type_lookup')
