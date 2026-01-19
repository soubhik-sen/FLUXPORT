"""add PO header table and related

Revision ID: aa1daf0b92aa
Revises: 9963ed28b2a9
Create Date: 2026-01-18 01:43:27.035848

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'aa1daf0b92aa'
down_revision: Union[str, Sequence[str], None] = '9963ed28b2a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    # 1. Create Purchase Org Lookup
    op.create_table(
        'purchase_org_lookup',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('org_code', sa.String(length=20), nullable=False),
        sa.Column('org_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('org_code')
    )

    # 1. Create Type Lookup
    op.create_table(
        'po_type_lookup',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('type_code', sa.String(length=20), nullable=False),
        sa.Column('type_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('type_code')
    )

    # 2. Create Status Lookup
    op.create_table(
        'po_status_lookup',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('status_code', sa.String(length=20), nullable=False),
        sa.Column('status_name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('status_code')
    )

    # 2. Update PO Header (Note: This assumes a fresh table creation)
    op.create_table(
        'po_header',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('po_number', sa.String(length=20), nullable=False),
        sa.Column('type_id', sa.Integer(), nullable=False),
        sa.Column('status_id', sa.Integer(), nullable=False),
        sa.Column('purchase_org_id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('vendor_id', sa.Integer(), nullable=False),
        sa.Column('order_date', sa.Date(), server_default=sa.func.current_date(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('total_amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('po_number'),
        sa.ForeignKeyConstraint(['type_id'], ['po_type_lookup.id']),
        sa.ForeignKeyConstraint(['status_id'], ['po_status_lookup.id']),
        sa.ForeignKeyConstraint(['purchase_org_id'], ['purchase_org_lookup.id']),
        sa.ForeignKeyConstraint(['company_id'], ['company_master.id']),
        sa.ForeignKeyConstraint(['vendor_id'], ['partner_master.id'])
    )

def downgrade() -> None:
    op.drop_table('po_header')
    op.drop_table('purchase_org_lookup')
    op.drop_table('po_status_lookup')
    op.drop_table('po_type_lookup')