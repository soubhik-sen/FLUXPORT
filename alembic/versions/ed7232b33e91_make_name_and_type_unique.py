"""make name and type unique

Revision ID: ed7232b33e91
Revises: 69f9728d06bc
Create Date: 2026-01-09 23:49:44.346261

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ed7232b33e91'
down_revision: Union[str, Sequence[str], None] = '69f9728d06bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def _constraint_exists(constraint_name: str, table_name: str) -> bool:
    bind = op.get_bind()
    sql = sa.text("""
        SELECT 1
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        WHERE c.conname = :cname
          AND t.relname = :tname
        LIMIT 1
    """)
    return bind.execute(sql, {"cname": constraint_name, "tname": table_name}).scalar() is not None

def upgrade() -> None:
    """Upgrade schema."""
    if not _constraint_exists("uq_masteraddr_name_type", "masteraddr"):
     op.create_unique_constraint("uq_masteraddr_name_type", "masteraddr", ["name", "type"])



def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_masteraddr_name_type", "masteraddr", type_="unique")

