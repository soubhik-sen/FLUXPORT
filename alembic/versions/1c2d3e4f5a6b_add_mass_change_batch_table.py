"""add mass change batch table

Revision ID: 1c2d3e4f5a6b
Revises: b7e5c2a1d4f9
Create Date: 2026-02-20 17:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1c2d3e4f5a6b"
down_revision: Union[str, None] = "b7e5c2a1d4f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mass_change_batch",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("dataset_key", sa.String(length=120), nullable=False),
        sa.Column("table_name", sa.String(length=120), nullable=False),
        sa.Column("user_email", sa.String(length=255), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("summary_json", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_mass_change_batch_dataset_key",
        "mass_change_batch",
        ["dataset_key"],
        unique=False,
    )
    op.create_index(
        "ix_mass_change_batch_user_email",
        "mass_change_batch",
        ["user_email"],
        unique=False,
    )
    op.create_index(
        "ix_mass_change_batch_expires_at",
        "mass_change_batch",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_mass_change_batch_expires_at", table_name="mass_change_batch")
    op.drop_index("ix_mass_change_batch_user_email", table_name="mass_change_batch")
    op.drop_index("ix_mass_change_batch_dataset_key", table_name="mass_change_batch")
    op.drop_table("mass_change_batch")
