"""add doc_text and text_val tables

Revision ID: n3o4p5q6r7s
Revises: m2n3o4p5q6r7
Create Date: 2026-02-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "n3o4p5q6r7s"
down_revision: Union[str, Sequence[str], None] = "m2n3o4p5q6r7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "doc_text",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("text_type_id", sa.Integer(), nullable=False),
        sa.Column("scope_kind", sa.String(length=20), nullable=False),
        sa.Column("po_type_id", sa.Integer(), nullable=True),
        sa.Column("ship_type_id", sa.Integer(), nullable=True),
        sa.Column("document_type_id", sa.Integer(), nullable=True),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("partner_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["text_type_id"], ["text_type_lookup.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["po_type_id"], ["po_type_lookup.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ship_type_id"], ["ship_type_lookup.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["document_type_id"], ["document_type_lookup.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["customer_master.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["partner_id"], ["partner_master.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            """
            (
                scope_kind = 'PO'
                AND po_type_id IS NOT NULL
                AND ship_type_id IS NULL
                AND document_type_id IS NULL
            )
            OR
            (
                scope_kind = 'SHIPMENT'
                AND po_type_id IS NULL
                AND ship_type_id IS NOT NULL
                AND document_type_id IS NULL
            )
            OR
            (
                scope_kind = 'DOCUMENT'
                AND po_type_id IS NULL
                AND ship_type_id IS NULL
                AND document_type_id IS NOT NULL
            )
            """,
            name="ck_doc_text_scope_target_match",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_doc_text_text_type_id", "doc_text", ["text_type_id"], unique=False)
    op.create_index("ix_doc_text_scope_kind", "doc_text", ["scope_kind"], unique=False)
    op.create_index("ix_doc_text_po_type_id", "doc_text", ["po_type_id"], unique=False)
    op.create_index("ix_doc_text_ship_type_id", "doc_text", ["ship_type_id"], unique=False)
    op.create_index("ix_doc_text_document_type_id", "doc_text", ["document_type_id"], unique=False)
    op.create_index("ix_doc_text_customer_id", "doc_text", ["customer_id"], unique=False)
    op.create_index("ix_doc_text_partner_id", "doc_text", ["partner_id"], unique=False)

    op.create_table(
        "text_val",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("doc_text_id", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("text_value", sa.Text(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("source_type", sa.String(length=30), nullable=True),
        sa.Column("external_ref", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["doc_text_id"], ["doc_text.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="ck_text_val_valid_range",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_text_val_doc_text_id", "text_val", ["doc_text_id"], unique=False)
    op.create_index("ix_text_val_language", "text_val", ["language"], unique=False)
    op.create_index("ix_text_val_doc_text_language", "text_val", ["doc_text_id", "language"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_text_val_doc_text_language", table_name="text_val")
    op.drop_index("ix_text_val_language", table_name="text_val")
    op.drop_index("ix_text_val_doc_text_id", table_name="text_val")
    op.drop_table("text_val")

    op.drop_index("ix_doc_text_partner_id", table_name="doc_text")
    op.drop_index("ix_doc_text_customer_id", table_name="doc_text")
    op.drop_index("ix_doc_text_document_type_id", table_name="doc_text")
    op.drop_index("ix_doc_text_ship_type_id", table_name="doc_text")
    op.drop_index("ix_doc_text_po_type_id", table_name="doc_text")
    op.drop_index("ix_doc_text_scope_kind", table_name="doc_text")
    op.drop_index("ix_doc_text_text_type_id", table_name="doc_text")
    op.drop_table("doc_text")
