"""add Shipment MILestones table and related

Revision ID: bad35861728d
Revises: 7a3f629bf2bb
Create Date: 2026-01-18 18:34:54.016320

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bad35861728d'
down_revision: Union[str, Sequence[str], None] = '7a3f629bf2bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Lookups
    op.create_table(
        'milestone_type_lookup',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('milestone_code', sa.String(length=20), nullable=False),
        sa.Column('milestone_name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('milestone_code')
    )

    op.create_table(
        'container_type_lookup',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('container_code', sa.String(length=10), nullable=False),
        sa.Column('container_name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('container_code')
    )

    # 2. Create Transactional Tables
    op.create_table(
        'shipment_milestone',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('shipment_header_id', sa.Integer(), nullable=False),
        sa.Column('milestone_id', sa.Integer(), nullable=False),
        sa.Column('event_datetime', sa.DateTime(), nullable=False),
        sa.Column('location', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['shipment_header_id'], ['shipment_header.id']),
        sa.ForeignKeyConstraint(['milestone_id'], ['milestone_type_lookup.id'])
    )

    op.create_table(
        'shipment_container',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('shipment_header_id', sa.Integer(), nullable=False),
        sa.Column('container_type_id', sa.Integer(), nullable=False),
        sa.Column('container_number', sa.String(length=20), nullable=False),
        sa.Column('seal_number', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('container_number'),
        sa.ForeignKeyConstraint(['shipment_header_id'], ['shipment_header.id']),
        sa.ForeignKeyConstraint(['container_type_id'], ['container_type_lookup.id'])
    )

def downgrade() -> None:
    op.drop_table('shipment_container')
    op.drop_table('shipment_milestone')
    op.drop_table('container_type_lookup')
    op.drop_table('milestone_type_lookup')
