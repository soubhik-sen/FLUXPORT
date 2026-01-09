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


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint("uq_masteraddr_name_type", "masteraddr", ["name", "type"])



def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("uq_masteraddr_name_type", "masteraddr", type_="unique")

