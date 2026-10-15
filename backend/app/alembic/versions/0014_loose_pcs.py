"""Add Loose Pcs catalogue, inventory, and transaction references.

Revision ID: 0014_loose_pcs
Revises: 0013_activity_log_entities
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_loose_pcs"
down_revision = "0013_activity_log_entities"
branch_labels = None
depends_on = None


ITEM_TYPES = "item_type IN ('tile', 'accessory', 'sanitary', 'loose_pcs')"
ITEM_TABLES = (
    ("invoice_items", "ck_invoice_items_type"),
    ("invoice_return_items", "ck_invoice_return_items_type"),
    ("return_exchange_items", "ck_return_exchange_items_type"),
)


def _has_table(name):
    return name in sa.inspect(op.get_bind()).get_table_names()


def _add_reference(table, column, ondelete):
    inspector = sa.inspect(op.get_bind())
    if column in {item["name"] for item in inspector.get_columns(table)}:
        return
    with op.batch_alter_table(table) as batch:
        batch.add_column(sa.Column(column, sa.Integer(), nullable=True))
        batch.create_foreign_key(
            f"fk_{table}_{column}_loose_pcs_products",
            "loose_pcs_products", [column], ["id"], ondelete=ondelete,
        )


def _replace_type_check(table, name):
    checks = {item["name"]: item["sqltext"] for item in sa.inspect(op.get_bind()).get_check_constraints(table)}
    if "loose_pcs" in (checks.get(name) or ""):
        return
    with op.batch_alter_table(table) as batch:
        if name in checks:
            batch.drop_constraint(name, type_="check")
        batch.create_check_constraint(name, ITEM_TYPES)


def upgrade():
    if not _has_table("loose_pcs_products"):
        op.create_table(
            "loose_pcs_products",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("size", sa.String(80), nullable=False),
            sa.Column("price", sa.Numeric(14, 2), nullable=False),
            sa.Column("sku", sa.String(40), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("name", "size", name="uq_loose_pcs_name_size"),
            sa.CheckConstraint("price >= 0", name="ck_loose_pcs_price"),
        )
    if not _has_table("loose_pcs_inventory"):
        op.create_table(
            "loose_pcs_inventory",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("loose_pcs_products.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("branch_id", "product_id", name="uq_loose_pcs_inventory_branch_product"),
            sa.CheckConstraint("quantity >= 0", name="ck_loose_pcs_inventory_quantity"),
        )
    for table in ("invoice_items", "return_exchange_items", "stock_transactions"):
        _add_reference(table, "loose_pcs_product_id", "RESTRICT")
    _add_reference("activity_log", "loose_pcs_product_id", "SET NULL")
    for table, name in ITEM_TABLES:
        _replace_type_check(table, name)
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes("activity_log")}
    if "ix_activity_log_loose_pcs_product_id" not in indexes:
        op.create_index("ix_activity_log_loose_pcs_product_id", "activity_log", ["loose_pcs_product_id"])


def downgrade():
    indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes("activity_log")}
    if "ix_activity_log_loose_pcs_product_id" in indexes:
        op.drop_index("ix_activity_log_loose_pcs_product_id", table_name="activity_log")
    for table, name in ITEM_TABLES:
        with op.batch_alter_table(table) as batch:
            batch.drop_constraint(name, type_="check")
            batch.create_check_constraint(name, "item_type IN ('tile', 'accessory', 'sanitary')")
    for table in ("activity_log", "stock_transactions", "return_exchange_items", "invoice_items"):
        foreign_keys = {item["name"] for item in sa.inspect(op.get_bind()).get_foreign_keys(table)}
        with op.batch_alter_table(table) as batch:
            name = f"fk_{table}_loose_pcs_product_id_loose_pcs_products"
            if name in foreign_keys:
                batch.drop_constraint(name, type_="foreignkey")
            batch.drop_column("loose_pcs_product_id")
    op.drop_table("loose_pcs_inventory")
    op.drop_table("loose_pcs_products")
