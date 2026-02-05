"""add forwarder_id to po_header

Revision ID: c2b7f3a1d9e4
Revises: e6e10a921188
Create Date: 2026-02-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2b7f3a1d9e4"
down_revision: Union[str, Sequence[str], None] = "e6e10a921188"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("po_header", sa.Column("forwarder_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_po_header_forwarder_id_partner_master",
        "po_header",
        "partner_master",
        ["forwarder_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_po_header_forwarder_id_partner_master", "po_header", type_="foreignkey")
    op.drop_column("po_header", "forwarder_id")
