"""add_audit_columns_to_docs

Revision ID: b6a8c0d2f5c1
Revises: 4a1b7f2c3d4e
Create Date: 2026-01-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b6a8c0d2f5c1"
down_revision: Union[str, Sequence[str], None] = "4a1b7f2c3d4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("po_header", sa.Column("created_by", sa.String(length=255), nullable=True))
    op.add_column("po_header", sa.Column("last_changed_by", sa.String(length=255), nullable=True))
    op.execute(
        "UPDATE po_header "
        "SET created_by = COALESCE(created_by, 'system@local'), "
        "last_changed_by = COALESCE(last_changed_by, 'system@local')"
    )
    op.alter_column("po_header", "created_by", nullable=False)
    op.alter_column("po_header", "last_changed_by", nullable=False)

    op.add_column("shipment_header", sa.Column("created_by", sa.String(length=255), nullable=True))
    op.add_column("shipment_header", sa.Column("last_changed_by", sa.String(length=255), nullable=True))
    op.execute(
        "UPDATE shipment_header "
        "SET created_by = COALESCE(created_by, 'system@local'), "
        "last_changed_by = COALESCE(last_changed_by, 'system@local')"
    )
    op.alter_column("shipment_header", "created_by", nullable=False)
    op.alter_column("shipment_header", "last_changed_by", nullable=False)

    op.add_column(
        "document_attachment",
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
    )
    op.add_column(
        "document_attachment",
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
    )
    op.add_column("document_attachment", sa.Column("created_by", sa.String(length=255), nullable=True))
    op.add_column("document_attachment", sa.Column("last_changed_by", sa.String(length=255), nullable=True))
    op.execute(
        "UPDATE document_attachment "
        "SET created_at = COALESCE(created_at, uploaded_at, now()), "
        "updated_at = COALESCE(updated_at, uploaded_at, now()), "
        "created_by = COALESCE(created_by, 'system@local'), "
        "last_changed_by = COALESCE(last_changed_by, 'system@local')"
    )
    op.alter_column("document_attachment", "created_at", nullable=False)
    op.alter_column("document_attachment", "updated_at", nullable=False)
    op.alter_column("document_attachment", "created_by", nullable=False)
    op.alter_column("document_attachment", "last_changed_by", nullable=False)


def downgrade() -> None:
    op.drop_column("document_attachment", "last_changed_by")
    op.drop_column("document_attachment", "created_by")
    op.drop_column("document_attachment", "updated_at")
    op.drop_column("document_attachment", "created_at")

    op.drop_column("shipment_header", "last_changed_by")
    op.drop_column("shipment_header", "created_by")

    op.drop_column("po_header", "last_changed_by")
    op.drop_column("po_header", "created_by")
