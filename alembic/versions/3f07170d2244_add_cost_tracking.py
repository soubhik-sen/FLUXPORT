"""add cost tracking

Revision ID: 3f07170d2244
Revises: bad35861728d
Create Date: 2026-01-18 18:38:03.331084

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f07170d2244'
down_revision: Union[str, Sequence[str], None] = 'bad35861728d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Cost Component Lookup
    op.create_table(
        'cost_component_lookup',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('component_code', sa.String(length=20), nullable=False),
        sa.Column('component_name', sa.String(length=100), nullable=False),
        sa.Column('is_tax', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('component_code')
    )

    # 2. Create Transactional Entry Table
    op.create_table(
        'landed_cost_entry',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('shipment_header_id', sa.Integer(), nullable=False),
        sa.Column('component_id', sa.Integer(), nullable=False),
        sa.Column('service_provider_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('invoice_reference', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['shipment_header_id'], ['shipment_header.id']),
        sa.ForeignKeyConstraint(['component_id'], ['cost_component_lookup.id']),
        sa.ForeignKeyConstraint(['service_provider_id'], ['partner_master.id'])
    )

def downgrade() -> None:
    op.drop_table('landed_cost_entry')
    op.drop_table('cost_component_lookup')
