"""create company master

Revision ID: 2d3c0a8356e0
Revises: 12f486433126
Create Date: 2026-01-18 00:34:22.812697

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d3c0a8356e0'
down_revision: Union[str, Sequence[str], None] = '12f486433126'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create the company_master table
    op.create_table(
        'company_master',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('company_code', sa.String(length=10), nullable=False),
        sa.Column('branch_code', sa.String(length=10), nullable=False),
        sa.Column('legal_name', sa.String(length=255), nullable=False),
        sa.Column('trade_name', sa.String(length=255), nullable=True),
        sa.Column('tax_id', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('addr_id', sa.Integer(), nullable=True),
        sa.Column('default_currency', sa.String(length=5), nullable=False, server_default='USD'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        
        # Constraints & Primary Key
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_code', name='uq_company_code'),
        sa.UniqueConstraint('tax_id', name='uq_tax_id'),
        
        # Foreign Key to your masteraddr table
        sa.ForeignKeyConstraint(['addr_id'], ['masteraddr.id'], name='fk_company_addr_id')
    )

    # 2. Add Indexes for performance (SAP codes are high-query fields)
    op.create_index('ix_company_master_company_code', 'company_master', ['company_code'])
    op.create_index('ix_company_master_branch_code', 'company_master', ['branch_code'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('ix_company_master_branch_code', table_name='company_master')
    op.drop_index('ix_company_master_company_code', table_name='company_master')
    
    # Drop the table
    op.drop_table('company_master')
