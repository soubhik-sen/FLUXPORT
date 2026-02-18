"""create document edit lock table

Revision ID: aa12bc34de56
Revises: a9d4c3e2f1b0
Create Date: 2026-02-18 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "aa12bc34de56"
down_revision: Union[str, None] = "a9d4c3e2f1b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_edit_lock",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("object_type", sa.String(length=32), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("owner_email", sa.String(length=255), nullable=False),
        sa.Column("owner_session_id", sa.String(length=120), nullable=False),
        sa.Column("lock_token_hash", sa.String(length=128), nullable=False),
        sa.Column(
            "acquired_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "heartbeat_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("released_at", sa.DateTime(), nullable=True),
        sa.Column("released_by", sa.String(length=255), nullable=True),
        sa.Column("release_reason", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        "ix_document_edit_lock_object_type",
        "document_edit_lock",
        ["object_type"],
        unique=False,
    )
    op.create_index(
        "ix_document_edit_lock_document_id",
        "document_edit_lock",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        "ix_document_edit_lock_owner_email",
        "document_edit_lock",
        ["owner_email"],
        unique=False,
    )
    op.create_index(
        "ix_document_edit_lock_lock_token_hash",
        "document_edit_lock",
        ["lock_token_hash"],
        unique=False,
    )
    op.create_index(
        "ix_document_edit_lock_expires_at",
        "document_edit_lock",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_document_edit_lock_expires_at", table_name="document_edit_lock")
    op.drop_index("ix_document_edit_lock_lock_token_hash", table_name="document_edit_lock")
    op.drop_index("ix_document_edit_lock_owner_email", table_name="document_edit_lock")
    op.drop_index("ix_document_edit_lock_document_id", table_name="document_edit_lock")
    op.drop_index("ix_document_edit_lock_object_type", table_name="document_edit_lock")
    op.drop_table("document_edit_lock")
