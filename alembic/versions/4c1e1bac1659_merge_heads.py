"""merge heads

Revision ID: 4c1e1bac1659
Revises: 9a3f1c4e6d9b, b6a8c0d2f5c1
Create Date: 2026-01-27 20:15:35.719923

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c1e1bac1659'
down_revision: Union[str, Sequence[str], None] = ('9a3f1c4e6d9b', 'b6a8c0d2f5c1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
