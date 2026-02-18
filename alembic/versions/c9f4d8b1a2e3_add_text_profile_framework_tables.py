"""add text profile framework tables

Revision ID: c9f4d8b1a2e3
Revises: b8e4d1a9c3f2
Create Date: 2026-02-15 23:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c9f4d8b1a2e3"
down_revision: Union[str, None] = "b8e4d1a9c3f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit_columns() -> list[sa.Column]:
    return [
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
        sa.Column(
            "created_by",
            sa.String(length=255),
            nullable=False,
            server_default=sa.text("'system@local'"),
        ),
        sa.Column(
            "last_changed_by",
            sa.String(length=255),
            nullable=False,
            server_default=sa.text("'system@local'"),
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "text_profile",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("object_type", sa.String(length=30), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column(
            "profile_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        *_audit_columns(),
        sa.UniqueConstraint("name", "object_type", name="uq_text_profile_name_object"),
    )
    op.create_index("ix_text_profile_name", "text_profile", ["name"], unique=False)
    op.create_index(
        "ix_text_profile_object_type",
        "text_profile",
        ["object_type"],
        unique=False,
    )

    op.create_table(
        "text_profile_rule",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("object_type", sa.String(length=30), nullable=False),
        sa.Column(
            "country_code",
            sa.String(length=8),
            nullable=False,
            server_default=sa.text("'*'"),
        ),
        sa.Column(
            "language",
            sa.String(length=10),
            nullable=False,
            server_default=sa.text("'en'"),
        ),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("100"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["profile_id"], ["text_profile.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_text_profile_rule_object_type",
        "text_profile_rule",
        ["object_type"],
        unique=False,
    )
    op.create_index(
        "ix_text_profile_rule_profile_id",
        "text_profile_rule",
        ["profile_id"],
        unique=False,
    )

    op.create_table(
        "profile_text_map",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("text_type_id", sa.Integer(), nullable=False),
        sa.Column(
            "sequence",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "is_mandatory",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_editable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["profile_id"], ["text_profile.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["text_type_id"], ["text_type_lookup.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "profile_id",
            "text_type_id",
            name="uq_profile_text_map_profile_type",
        ),
    )
    op.create_index(
        "ix_profile_text_map_profile_id",
        "profile_text_map",
        ["profile_id"],
        unique=False,
    )
    op.create_index(
        "ix_profile_text_map_text_type_id",
        "profile_text_map",
        ["text_type_id"],
        unique=False,
    )

    op.create_table(
        "profile_text_value",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("profile_text_map_id", sa.Integer(), nullable=False),
        sa.Column(
            "language",
            sa.String(length=10),
            nullable=False,
            server_default=sa.text("'en'"),
        ),
        sa.Column("country_code", sa.String(length=8), nullable=True),
        sa.Column("text_value", sa.Text(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["profile_text_map_id"],
            ["profile_text_map.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_profile_text_value_map_id",
        "profile_text_value",
        ["profile_text_map_id"],
        unique=False,
    )

    op.create_table(
        "po_text",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("po_header_id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=True),
        sa.Column("profile_version", sa.Integer(), nullable=True),
        sa.Column("text_type_id", sa.Integer(), nullable=False),
        sa.Column(
            "language",
            sa.String(length=10),
            nullable=False,
            server_default=sa.text("'en'"),
        ),
        sa.Column("text_value", sa.Text(), nullable=False),
        sa.Column(
            "is_user_edited",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["po_header_id"], ["po_header.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["text_profile.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["text_type_id"], ["text_type_lookup.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "po_header_id",
            "text_type_id",
            "language",
            name="uq_po_text_unique",
        ),
    )
    op.create_index("ix_po_text_po_header_id", "po_text", ["po_header_id"], unique=False)

    op.create_table(
        "shipment_text",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("shipment_header_id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=True),
        sa.Column("profile_version", sa.Integer(), nullable=True),
        sa.Column("text_type_id", sa.Integer(), nullable=False),
        sa.Column(
            "language",
            sa.String(length=10),
            nullable=False,
            server_default=sa.text("'en'"),
        ),
        sa.Column("text_value", sa.Text(), nullable=False),
        sa.Column(
            "is_user_edited",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        *_audit_columns(),
        sa.ForeignKeyConstraint(
            ["shipment_header_id"],
            ["shipment_header.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["profile_id"], ["text_profile.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["text_type_id"], ["text_type_lookup.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "shipment_header_id",
            "text_type_id",
            "language",
            name="uq_shipment_text_unique",
        ),
    )
    op.create_index(
        "ix_shipment_text_header_id",
        "shipment_text",
        ["shipment_header_id"],
        unique=False,
    )

    bind = op.get_bind()
    text_profile = sa.table(
        "text_profile",
        sa.column("id", sa.Integer()),
        sa.column("name", sa.String(length=120)),
        sa.column("object_type", sa.String(length=30)),
        sa.column("description", sa.String(length=255)),
        sa.column("profile_version", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
    )
    bind.execute(
        text_profile.insert(),
        [
            {
                "name": "po_text_profile",
                "object_type": "PO",
                "description": "Default PO text profile",
                "profile_version": 1,
                "is_active": True,
            },
            {
                "name": "shipment_text_profile",
                "object_type": "SHIPMENT",
                "description": "Default shipment text profile",
                "profile_version": 1,
                "is_active": True,
            },
        ],
    )

    rows = bind.execute(
        sa.select(text_profile.c.id, text_profile.c.name)
        .where(text_profile.c.name.in_(["po_text_profile", "shipment_text_profile"]))
    ).all()
    profile_id_by_name = {row.name: row.id for row in rows}
    if profile_id_by_name:
        text_profile_rule = sa.table(
            "text_profile_rule",
            sa.column("object_type", sa.String(length=30)),
            sa.column("country_code", sa.String(length=8)),
            sa.column("language", sa.String(length=10)),
            sa.column("profile_id", sa.Integer()),
            sa.column("priority", sa.Integer()),
            sa.column("is_active", sa.Boolean()),
        )
        inserts = []
        po_profile_id = profile_id_by_name.get("po_text_profile")
        ship_profile_id = profile_id_by_name.get("shipment_text_profile")
        if po_profile_id is not None:
            inserts.append(
                {
                    "object_type": "PO",
                    "country_code": "*",
                    "language": "en",
                    "profile_id": po_profile_id,
                    "priority": 100,
                    "is_active": True,
                }
            )
        if ship_profile_id is not None:
            inserts.append(
                {
                    "object_type": "SHIPMENT",
                    "country_code": "*",
                    "language": "en",
                    "profile_id": ship_profile_id,
                    "priority": 100,
                    "is_active": True,
                }
            )
        if inserts:
            bind.execute(text_profile_rule.insert(), inserts)


def downgrade() -> None:
    op.drop_index("ix_shipment_text_header_id", table_name="shipment_text")
    op.drop_table("shipment_text")

    op.drop_index("ix_po_text_po_header_id", table_name="po_text")
    op.drop_table("po_text")

    op.drop_index("ix_profile_text_value_map_id", table_name="profile_text_value")
    op.drop_table("profile_text_value")

    op.drop_index("ix_profile_text_map_text_type_id", table_name="profile_text_map")
    op.drop_index("ix_profile_text_map_profile_id", table_name="profile_text_map")
    op.drop_table("profile_text_map")

    op.drop_index("ix_text_profile_rule_profile_id", table_name="text_profile_rule")
    op.drop_index("ix_text_profile_rule_object_type", table_name="text_profile_rule")
    op.drop_table("text_profile_rule")

    op.drop_index("ix_text_profile_object_type", table_name="text_profile")
    op.drop_index("ix_text_profile_name", table_name="text_profile")
    op.drop_table("text_profile")
