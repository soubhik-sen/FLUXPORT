"""create_customer_master_table

Revision ID: 7f3c2a9d5b6e
Revises: 22a95c9bdca1
Create Date: 2026-01-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f3c2a9d5b6e'
down_revision: Union[str, Sequence[str], None] = '22a95c9bdca1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'customer_role_lookup',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('role_code', sa.String(length=30), nullable=False),
        sa.Column('role_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_code'),
    )

    op.create_table(
        'customer_master',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('customer_identifier', sa.String(length=20), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.Column('legal_name', sa.String(length=255), nullable=False),
        sa.Column('trade_name', sa.String(length=255), nullable=True),
        sa.Column('tax_registration_id', sa.String(length=50), nullable=True),
        sa.Column('payment_terms_code', sa.String(length=20), nullable=True),
        sa.Column('preferred_currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('addr_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('customer_identifier'),
        sa.UniqueConstraint('tax_registration_id'),
        sa.ForeignKeyConstraint(['role_id'], ['customer_role_lookup.id'], name='fk_customer_role_id'),
        sa.ForeignKeyConstraint(['addr_id'], ['masteraddr.id'], name='fk_customer_addr_id'),
    )


def downgrade() -> None:
    op.drop_table('customer_master')
    op.drop_table('customer_role_lookup')
