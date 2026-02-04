"""cleanup unintended changes

Revision ID: ef12ab34cd56
Revises: a38ac7b6c111
Create Date: 2026-02-03
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "ef12ab34cd56"
down_revision = "a38ac7b6c111"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE shipment_header DROP CONSTRAINT IF EXISTS shipment_header_type_id_fkey")
    op.execute("ALTER TABLE shipment_header DROP COLUMN IF EXISTS type_id")
    op.execute("ALTER TABLE po_schedule_line DROP COLUMN IF EXISTS shipments")
    op.execute("DROP TABLE IF EXISTS ship_type_lookup")


def downgrade() -> None:
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
    op.execute("ALTER TABLE po_schedule_line ADD COLUMN IF NOT EXISTS shipments INTEGER")
    op.execute("ALTER TABLE shipment_header ADD COLUMN IF NOT EXISTS type_id INTEGER")
    op.execute(
        "ALTER TABLE shipment_header ADD CONSTRAINT shipment_header_type_id_fkey FOREIGN KEY (type_id) REFERENCES ship_type_lookup (id)"
    )
