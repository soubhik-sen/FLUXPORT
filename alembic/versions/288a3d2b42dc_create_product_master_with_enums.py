"""create_product_master_with_enums

Revision ID: 288a3d2b42dc
Revises: 02515c610e33
Create Date: 2026-01-18 00:58:43.942363

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '288a3d2b42dc'
down_revision: Union[str, Sequence[str], None] = '02515c610e33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. Product Type Lookup
    op.create_table(
        'product_type_lookup',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('type_code', sa.String(length=20), nullable=False),
        sa.Column('type_name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('type_code')
    )

    # 2. UOM Lookup
    op.create_table(
        'uom_lookup',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('uom_code', sa.String(length=10), nullable=False),
        sa.Column('uom_name', sa.String(length=100), nullable=False),
        sa.Column('uom_class', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uom_code')
    )

    # 3. Product Master
    op.create_table(
        'product_master',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('sku_identifier', sa.String(length=40), nullable=False),
        sa.Column('type_id', sa.Integer(), nullable=False),
        sa.Column('uom_id', sa.Integer(), nullable=False),
        sa.Column('short_description', sa.String(length=255), nullable=False),
        sa.Column('detailed_description', sa.String(length=1000), nullable=True),
        sa.Column('hs_code', sa.String(length=15), nullable=True),
        sa.Column('country_of_origin', sa.String(length=2), nullable=True),
        sa.Column('weight_kg', sa.Float(), nullable=True),
        sa.Column('volume_m3', sa.Float(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sku_identifier'),
        sa.ForeignKeyConstraint(['type_id'], ['product_type_lookup.id']),
        sa.ForeignKeyConstraint(['uom_id'], ['uom_lookup.id'])
    )

def downgrade() -> None:
    op.drop_table('product_master')
    op.drop_table('uom_lookup')
    op.drop_table('product_type_lookup')
