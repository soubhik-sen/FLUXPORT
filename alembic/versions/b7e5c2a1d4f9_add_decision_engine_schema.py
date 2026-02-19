"""add decision engine schema compatibility tables

Revision ID: b7e5c2a1d4f9
Revises: aa12bc34de56
Create Date: 2026-02-18 20:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "b7e5c2a1d4f9"
down_revision: Union[str, None] = "aa12bc34de56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'hit_policy_enum'
            ) THEN
                CREATE TYPE hit_policy_enum AS ENUM ('FIRST_HIT', 'COLLECT_ALL', 'UNIQUE');
            END IF;
        END$$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'resolution_strategy_enum'
            ) THEN
                CREATE TYPE resolution_strategy_enum AS ENUM ('DIRECT', 'ASSOCIATION', 'EXTERNAL');
            END IF;
        END$$;
        """
    )

    op.create_table(
        "decision_tables",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column(
            "object_type",
            sa.String(),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column(
            "description",
            sa.String(),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column(
            "hit_policy",
            postgresql.ENUM(
                "FIRST_HIT",
                "COLLECT_ALL",
                "UNIQUE",
                name="hit_policy_enum",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'FIRST_HIT'"),
        ),
        sa.Column(
            "input_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "output_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index(
        "ix_decision_tables_slug",
        "decision_tables",
        ["slug"],
        unique=True,
    )
    op.create_index(
        "ix_decision_tables_object_type",
        "decision_tables",
        ["object_type"],
        unique=False,
    )

    op.create_table(
        "decision_rules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "table_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("decision_tables.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "logic",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_decision_rules_logic",
        "decision_rules",
        ["logic"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"logic": "jsonb_path_ops"},
    )

    op.create_table(
        "attribute_registry",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("target_object", sa.String(), nullable=False),
        sa.Column("attribute_name", sa.String(), nullable=False),
        sa.Column(
            "resolution_strategy",
            postgresql.ENUM(
                "DIRECT",
                "ASSOCIATION",
                "EXTERNAL",
                name="resolution_strategy_enum",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'DIRECT'"),
        ),
        sa.Column(
            "path_logic",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.UniqueConstraint(
            "target_object",
            "attribute_name",
            name="uq_attribute_registry_target_attr",
        ),
    )
    op.create_index(
        "ix_attribute_registry_target_object",
        "attribute_registry",
        ["target_object"],
        unique=False,
    )
    op.create_index(
        "ix_attribute_registry_target_attr",
        "attribute_registry",
        ["target_object", "attribute_name"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_attribute_registry_target_attr", table_name="attribute_registry")
    op.drop_index("ix_attribute_registry_target_object", table_name="attribute_registry")
    op.drop_table("attribute_registry")

    op.drop_index("ix_decision_rules_logic", table_name="decision_rules")
    op.drop_table("decision_rules")

    op.drop_index("ix_decision_tables_object_type", table_name="decision_tables")
    op.drop_index("ix_decision_tables_slug", table_name="decision_tables")
    op.drop_table("decision_tables")

    sa.Enum(name="resolution_strategy_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="hit_policy_enum").drop(op.get_bind(), checkfirst=True)
