"""create metadata framework tables

Revision ID: b8e4d1a9c3f2
Revises: f4b9c2d1e0a7
Create Date: 2026-02-13 20:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b8e4d1a9c3f2"
down_revision: Union[str, None] = "f4b9c2d1e0a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "metadata_registry",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("type_key", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("json_schema", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("type_key", name="uq_metadata_registry_type_key"),
    )
    op.create_index(
        "ix_metadata_registry_type_key",
        "metadata_registry",
        ["type_key"],
        unique=False,
    )

    op.create_table(
        "metadata_version",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("registry_id", sa.Integer(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("published_by", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["registry_id"],
            ["metadata_registry.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "registry_id",
            "version_no",
            name="uq_metadata_version_registry_version",
        ),
    )
    op.create_index(
        "ix_metadata_version_registry_id",
        "metadata_version",
        ["registry_id"],
        unique=False,
    )

    op.create_table(
        "metadata_audit_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("registry_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("actor_email", sa.String(length=255), nullable=True),
        sa.Column("from_version_id", sa.Integer(), nullable=True),
        sa.Column("to_version_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["registry_id"],
            ["metadata_registry.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_metadata_audit_log_registry_id",
        "metadata_audit_log",
        ["registry_id"],
        unique=False,
    )
    op.create_index(
        "ix_metadata_audit_log_action",
        "metadata_audit_log",
        ["action"],
        unique=False,
    )

    metadata_registry = sa.table(
        "metadata_registry",
        sa.column("type_key", sa.String(length=120)),
        sa.column("display_name", sa.String(length=160)),
        sa.column("description", sa.String(length=500)),
        sa.column("json_schema", sa.Text()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        metadata_registry,
        [
            {
                "type_key": "endpoint_metadata",
                "display_name": "Endpoint Metadata",
                "description": "UI/API endpoint wiring metadata.",
                "json_schema": None,
                "is_active": True,
            },
            {
                "type_key": "ui_text_metadata",
                "display_name": "UI Text Metadata",
                "description": "Translatable/maintainable UI text metadata.",
                "json_schema": None,
                "is_active": True,
            },
            {
                "type_key": "create_po_route_metadata",
                "display_name": "Create PO Route Metadata",
                "description": "User-email based routing between old/new Create PO screens.",
                "json_schema": None,
                "is_active": True,
            },
            {
                "type_key": "role_scope_policy",
                "display_name": "Role Scope Policy Metadata",
                "description": "Role-scope and policy controls for endpoint access/scoping.",
                "json_schema": None,
                "is_active": True,
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_metadata_audit_log_action", table_name="metadata_audit_log")
    op.drop_index("ix_metadata_audit_log_registry_id", table_name="metadata_audit_log")
    op.drop_table("metadata_audit_log")

    op.drop_index("ix_metadata_version_registry_id", table_name="metadata_version")
    op.drop_table("metadata_version")

    op.drop_index("ix_metadata_registry_type_key", table_name="metadata_registry")
    op.drop_table("metadata_registry")
