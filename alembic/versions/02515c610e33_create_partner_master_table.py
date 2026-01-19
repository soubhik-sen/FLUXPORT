"""create_partner_master_table

Revision ID: 02515c610e33
Revises: 2d3c0a8356e0
Create Date: 2026-01-18 00:46:16.714645

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '02515c610e33'
down_revision: Union[str, Sequence[str], None] = '2d3c0a8356e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Role Lookup Table
    op.create_table(
        'partner_role_lookup',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('role_code', sa.String(length=30), nullable=False),
        sa.Column('role_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_code')
    )

    # 2. Create Partner Master referencing the lookup
    op.create_table(
        'partner_master',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('partner_identifier', sa.String(length=20), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False), # Reference to lookup
        sa.Column('legal_name', sa.String(length=255), nullable=False),
        sa.Column('trade_name', sa.String(length=255), nullable=True),
        sa.Column('tax_registration_id', sa.String(length=50), nullable=True),
        sa.Column('preferred_currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('addr_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('partner_identifier'),
        sa.ForeignKeyConstraint(['role_id'], ['partner_role_lookup.id'], name='fk_partner_role_id'),
        sa.ForeignKeyConstraint(['addr_id'], ['masteraddr.id'], name='fk_partner_addr_id')
    )

def downgrade() -> None:
    op.drop_table('partner_master')
    op.drop_table('partner_role_lookup')