"""restore ship type lookup and shipment type_id

Revision ID: h7a8b9c0d1e2
Revises: g1h2i3j4k5l6
Create Date: 2026-02-06

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "h7a8b9c0d1e2"
down_revision: Union[str, Sequence[str], None] = "g1h2i3j4k5l6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS ship_type_lookup (
            id SERIAL PRIMARY KEY,
            type_code VARCHAR(20) NOT NULL,
            type_name VARCHAR(100) NOT NULL,
            description VARCHAR(255),
            is_active BOOLEAN NOT NULL,
            created_at TIMESTAMP DEFAULT now() NOT NULL
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_ship_type_lookup_type_code ON ship_type_lookup (type_code)"
    )
    op.execute(
        """
        INSERT INTO ship_type_lookup (type_code, type_name, description, is_active)
        VALUES ('STD', 'Standard', 'Default shipment type', true)
        ON CONFLICT (type_code) DO NOTHING
        """
    )
    op.execute("ALTER TABLE shipment_header ADD COLUMN IF NOT EXISTS type_id INTEGER")
    op.execute(
        """
        UPDATE shipment_header
        SET type_id = (
            SELECT id FROM ship_type_lookup WHERE type_code = 'STD' LIMIT 1
        )
        WHERE type_id IS NULL
        """
    )
    op.execute("ALTER TABLE shipment_header ALTER COLUMN type_id SET NOT NULL")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'shipment_header_type_id_fkey'
            ) THEN
                ALTER TABLE shipment_header
                ADD CONSTRAINT shipment_header_type_id_fkey
                FOREIGN KEY (type_id) REFERENCES ship_type_lookup (id);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE shipment_header DROP CONSTRAINT IF EXISTS shipment_header_type_id_fkey")
    op.execute("ALTER TABLE shipment_header DROP COLUMN IF EXISTS type_id")
    op.execute("DROP INDEX IF EXISTS ix_ship_type_lookup_type_code")
    op.execute("DROP TABLE IF EXISTS ship_type_lookup")
