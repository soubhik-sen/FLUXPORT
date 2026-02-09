"""add_material_master_module

Revision ID: p1q2r3s4t5u6
Revises: n3o4p5q6r7s
Create Date: 2026-02-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "p1q2r3s4t5u6"
down_revision: Union[str, Sequence[str], None] = "n3o4p5q6r7s"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "product_type_lookup",
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
    )
    op.add_column(
        "product_type_lookup",
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
    )
    op.add_column(
        "product_type_lookup",
        sa.Column("created_by", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "product_type_lookup",
        sa.Column("last_changed_by", sa.String(length=255), nullable=True),
    )
    op.execute(
        "UPDATE product_type_lookup "
        "SET created_at = COALESCE(created_at, now()), "
        "updated_at = COALESCE(updated_at, now()), "
        "created_by = COALESCE(created_by, 'system@local'), "
        "last_changed_by = COALESCE(last_changed_by, 'system@local')"
    )
    op.alter_column("product_type_lookup", "created_at", nullable=False)
    op.alter_column("product_type_lookup", "updated_at", nullable=False)
    op.alter_column("product_type_lookup", "created_by", nullable=False)
    op.alter_column("product_type_lookup", "last_changed_by", nullable=False)

    op.add_column(
        "uom_lookup",
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
    )
    op.add_column(
        "uom_lookup",
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
    )
    op.add_column(
        "uom_lookup",
        sa.Column("created_by", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "uom_lookup",
        sa.Column("last_changed_by", sa.String(length=255), nullable=True),
    )
    op.execute(
        "UPDATE uom_lookup "
        "SET created_at = COALESCE(created_at, now()), "
        "updated_at = COALESCE(updated_at, now()), "
        "created_by = COALESCE(created_by, 'system@local'), "
        "last_changed_by = COALESCE(last_changed_by, 'system@local')"
    )
    op.alter_column("uom_lookup", "created_at", nullable=False)
    op.alter_column("uom_lookup", "updated_at", nullable=False)
    op.alter_column("uom_lookup", "created_by", nullable=False)
    op.alter_column("uom_lookup", "last_changed_by", nullable=False)

    op.rename_table("product_master", "material_master")

    op.alter_column(
        "material_master",
        "sku_identifier",
        new_column_name="part_number",
        existing_type=sa.String(length=40),
        existing_nullable=False,
    )
    op.alter_column(
        "material_master",
        "type_id",
        new_column_name="material_type_id",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "material_master",
        "uom_id",
        new_column_name="base_uom_id",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )

    op.alter_column(
        "material_master",
        "weight_kg",
        type_=sa.Numeric(15, 4),
        existing_type=sa.Float(),
        existing_nullable=True,
    )
    op.alter_column(
        "material_master",
        "volume_m3",
        type_=sa.Numeric(15, 4),
        existing_type=sa.Float(),
        existing_nullable=True,
    )

    op.add_column("material_master", sa.Column("created_by", sa.String(length=255), nullable=True))
    op.add_column("material_master", sa.Column("last_changed_by", sa.String(length=255), nullable=True))
    op.execute(
        "UPDATE material_master "
        "SET created_by = COALESCE(created_by, 'system@local'), "
        "last_changed_by = COALESCE(last_changed_by, 'system@local')"
    )
    op.alter_column("material_master", "created_by", nullable=False)
    op.alter_column("material_master", "last_changed_by", nullable=False)

    op.create_table(
        "material_text",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("language_code", sa.String(length=2), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("long_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("last_changed_by", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["material_id"], ["material_master.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("material_id", "language_code", name="uq_material_text_material_language"),
    )

    op.create_table(
        "material_plant_data",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("is_purchasable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("safety_stock_qty", sa.Numeric(15, 4), nullable=True),
        sa.Column("default_lead_time", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("last_changed_by", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["material_id"], ["material_master.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["branch_id"], ["partner_master.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "material_uom_conversion",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("alternative_uom_id", sa.Integer(), nullable=False),
        sa.Column("numerator", sa.Numeric(15, 4), nullable=False),
        sa.Column("denominator", sa.Numeric(15, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("last_changed_by", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["material_id"], ["material_master.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["alternative_uom_id"], ["uom_lookup.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "material_supplier_map",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("supplier_part_number", sa.String(length=64), nullable=True),
        sa.Column("is_preferred", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("min_order_qty", sa.Numeric(15, 4), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("last_changed_by", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["material_id"], ["material_master.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supplier_id"], ["partner_master.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "material_customer_map",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("material_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("customer_part_number", sa.String(length=64), nullable=True),
        sa.Column("sales_uom_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("last_changed_by", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["material_id"], ["material_master.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["partner_master.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sales_uom_id"], ["uom_lookup.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("material_customer_map")
    op.drop_table("material_supplier_map")
    op.drop_table("material_uom_conversion")
    op.drop_table("material_plant_data")
    op.drop_table("material_text")

    op.drop_column("material_master", "last_changed_by")
    op.drop_column("material_master", "created_by")

    op.alter_column(
        "material_master",
        "weight_kg",
        type_=sa.Float(),
        existing_type=sa.Numeric(15, 4),
        existing_nullable=True,
    )
    op.alter_column(
        "material_master",
        "volume_m3",
        type_=sa.Float(),
        existing_type=sa.Numeric(15, 4),
        existing_nullable=True,
    )

    op.alter_column(
        "material_master",
        "base_uom_id",
        new_column_name="uom_id",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "material_master",
        "material_type_id",
        new_column_name="type_id",
        existing_type=sa.Integer(),
        existing_nullable=False,
    )
    op.alter_column(
        "material_master",
        "part_number",
        new_column_name="sku_identifier",
        existing_type=sa.String(length=40),
        existing_nullable=False,
    )

    op.rename_table("material_master", "product_master")

    op.drop_column("uom_lookup", "last_changed_by")
    op.drop_column("uom_lookup", "created_by")
    op.drop_column("uom_lookup", "updated_at")
    op.drop_column("uom_lookup", "created_at")

    op.drop_column("product_type_lookup", "last_changed_by")
    op.drop_column("product_type_lookup", "created_by")
    op.drop_column("product_type_lookup", "updated_at")
    op.drop_column("product_type_lookup", "created_at")
