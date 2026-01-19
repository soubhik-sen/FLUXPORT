"""add_qualifier_and_pricing_tables

Revision ID: 9963ed28b2a9
Revises: 288a3d2b42dc
Create Date: 2026-01-18 01:03:34.792782

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9963ed28b2a9'
down_revision: Union[str, Sequence[str], None] = '288a3d2b42dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    
    op.create_table(
        'pricing_type_lookup',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('type_code', sa.String(length=20), nullable=False),
        sa.Column('type_name', sa.String(length=100), nullable=False),
        sa.Column('is_deduction', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('type_code')
    )

    # 2. Create System Qualifier Table (Lookup/Config)
    op.create_table(
        'system_qualifier',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category', 'code', name='uq_category_code')
    )
    op.create_index('ix_system_qualifier_category', 'system_qualifier', ['category'])

    # 3. Create Pricing Condition Table
    op.create_table(
        'pricing_condition',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('partner_id', sa.Integer(), nullable=True),
        sa.Column('type_id', sa.Integer(), nullable=False), # Reference to lookup
        sa.Column('rate', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('valid_from', sa.Date(), nullable=False),
        sa.Column('valid_to', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['product_id'], ['product_master.id'], name='fk_pricing_product_id'),
        sa.ForeignKeyConstraint(['partner_id'], ['partner_master.id'], name='fk_pricing_partner_id'),
        sa.ForeignKeyConstraint(['type_id'], ['pricing_type_lookup.id'], name='fk_pricing_type_id')
    )

def downgrade() -> None:
    # Drop Tables
    op.drop_table('pricing_condition')
    op.drop_index('ix_system_qualifier_category', table_name='system_qualifier')
    op.drop_table('system_qualifier')
    op.drop_table('pricing_type_lookup')

