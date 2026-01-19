"""add PO item table and related

Revision ID: ca099de294fe
Revises: aa1daf0b92aa
Create Date: 2026-01-18 01:56:46.884046

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca099de294fe'
down_revision: Union[str, Sequence[str], None] = 'aa1daf0b92aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Item Status Lookup
    op.create_table(
        'po_item_status_lookup',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('status_code', sa.String(length=20), nullable=False),
        sa.Column('status_name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('status_code')
    )

    # 2. Create PO Item Table
    op.create_table(
        'po_item',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('po_header_id', sa.Integer(), nullable=False),
        sa.Column('item_number', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('status_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=15, scale=3), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('line_total', sa.Numeric(precision=15, scale=2), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['po_header_id'], ['po_header.id']),
        sa.ForeignKeyConstraint(['product_id'], ['product_master.id']),
        sa.ForeignKeyConstraint(['status_id'], ['po_item_status_lookup.id'])
    )

def downgrade() -> None:
    op.drop_table('po_item')
    op.drop_table('po_item_status_lookup')
