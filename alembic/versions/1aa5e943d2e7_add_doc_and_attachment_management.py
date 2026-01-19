"""add doc and attachment management

Revision ID: 1aa5e943d2e7
Revises: 3f07170d2244
Create Date: 2026-01-18 18:40:11.143944

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1aa5e943d2e7'
down_revision: Union[str, Sequence[str], None] = '3f07170d2244'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Document Type Lookup
    op.create_table(
        'document_type_lookup',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('type_code', sa.String(length=20), nullable=False),
        sa.Column('type_name', sa.String(length=100), nullable=False),
        sa.Column('is_mandatory', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('type_code')
    )

    # 2. Create Document Attachment Table
    op.create_table(
        'document_attachment',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('type_id', sa.Integer(), nullable=False),
        sa.Column('file_name', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_extension', sa.String(length=10), nullable=False),
        sa.Column('file_size_kb', sa.Integer(), nullable=True),
        sa.Column('shipment_id', sa.Integer(), nullable=True),
        sa.Column('po_header_id', sa.Integer(), nullable=True),
        sa.Column('partner_id', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('uploaded_by_id', sa.Integer(), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['type_id'], ['document_type_lookup.id']),
        sa.ForeignKeyConstraint(['shipment_id'], ['shipment_header.id']),
        sa.ForeignKeyConstraint(['po_header_id'], ['po_header.id']),
        sa.ForeignKeyConstraint(['partner_id'], ['partner_master.id'])
    )

def downgrade() -> None:
    op.drop_table('document_attachment')
    op.drop_table('document_type_lookup')
