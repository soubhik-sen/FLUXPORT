"""number range table create

Revision ID: 22a95c9bdca1
Revises: 55271a5f594c
Create Date: 2026-01-23 18:50:32.667756

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '22a95c9bdca1'
down_revision: Union[str, Sequence[str], None] = '55271a5f594c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'sys_number_ranges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('doc_category', sa.String(length=20), nullable=False),
        sa.Column('doc_type_id', sa.Integer(), nullable=False),
        sa.Column('prefix', sa.String(length=10), nullable=False),
        sa.Column('current_value', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('padding', sa.Integer(), server_default='5', nullable=False),
        sa.Column('include_year', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('doc_category', 'doc_type_id', name='uix_category_type')
    )
    # Index for fast lookups during the document save transaction
    op.create_index('ix_number_range_lookup', 'sys_number_ranges', ['doc_category', 'doc_type_id'])


def downgrade() -> None:
    op.drop_index('ix_number_range_lookup', table_name='sys_number_ranges')
    op.drop_table('sys_number_ranges')
