"""rbac create user_countries

Revision ID: c0495ba9c2d1
Revises: 2cfff2015862
Create Date: 2026-01-13 14:36:29.983609

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c0495ba9c2d1'
down_revision: Union[str, Sequence[str], None] = '2cfff2015862'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_countries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_countries_user",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "user_id",
            "country_code",
            name="uq_user_countries_user_country",
        ),
    )

    op.create_index(
        "ix_user_countries_user_id",
        "user_countries",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_countries_user_id", table_name="user_countries")
    op.drop_table("user_countries")
