"""Add Master Sanitary catalogue, inventory and sale references.

Revision ID: 0015_master_sanitary
Revises: 0014_loose_pcs
"""

from alembic import op
import sqlalchemy as sa


revision = "0015_master_sanitary"
down_revision = "0014_loose_pcs"
branch_labels = None
depends_on = None

OLD_TYPES = "item_type IN ('tile', 'accessory', 'sanitary', 'loose_pcs')"
NEW_TYPES = "item_type IN ('tile', 'accessory', 'sanitary', 'loose_pcs', 'master_sanitary')"
ITEM_TABLES = (
    ("invoice_items", "ck_invoice_items_type"),
    ("invoice_return_items", "ck_invoice_return_items_type"),
    ("return_exchange_items", "ck_return_exchange_items_type"),
)
REFERENCES = (
    ("invoice_items", "fk_invoice_items_ms_product", "RESTRICT"),
    ("return_exchange_items", "fk_return_exchange_items_ms_product", "RESTRICT"),
    ("stock_transactions", "fk_stock_transactions_ms_product", "RESTRICT"),
    ("activity_log", "fk_activity_log_ms_product", "SET NULL"),
)
COLUMN = "master_sanitary_product_id"


def _replace_check(table, name, expression):
    checks = {item["name"] for item in sa.inspect(op.get_bind()).get_check_constraints(table)}
    with op.batch_alter_table(table) as batch:
        if name in checks:
            batch.drop_constraint(name, type_="check")
        batch.create_check_constraint(name, expression)


def upgrade():
    if "master_sanitary_products" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "master_sanitary_products",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("color", sa.String(80), nullable=False),
            sa.Column("normalized_name", sa.String(160), nullable=False),
            sa.Column("normalized_color", sa.String(80), nullable=False),
            sa.Column("sku", sa.String(40), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("normalized_name", "normalized_color", name="uq_ms_product_identity"),
            sa.UniqueConstraint("sku", name="uq_ms_product_sku"),
        )
    if "master_sanitary_inventory" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "master_sanitary_inventory",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id", name="fk_ms_inventory_branch", ondelete="RESTRICT"), nullable=False),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("master_sanitary_products.id", name="fk_ms_inventory_product", ondelete="RESTRICT"), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("price", sa.Numeric(14, 2), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("branch_id", "product_id", name="uq_ms_inventory_branch_product"),
            sa.CheckConstraint("quantity >= 0", name="ck_ms_inventory_quantity"),
            sa.CheckConstraint("price IS NULL OR price >= 0", name="ck_ms_inventory_price"),
        )
    for table, fk_name, ondelete in REFERENCES:
        inspector = sa.inspect(op.get_bind())
        existing = {column["name"] for column in inspector.get_columns(table)}
        foreign_keys = {item["name"] for item in inspector.get_foreign_keys(table)}
        if COLUMN not in existing or fk_name not in foreign_keys:
            with op.batch_alter_table(table) as batch:
                if COLUMN not in existing:
                    batch.add_column(sa.Column(COLUMN, sa.Integer(), nullable=True))
                if fk_name not in foreign_keys:
                    batch.create_foreign_key(fk_name, "master_sanitary_products", [COLUMN], ["id"], ondelete=ondelete)
    for table, name in ITEM_TABLES:
        _replace_check(table, name, NEW_TYPES)
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("activity_log")}
    if "ix_activity_log_ms_product" not in indexes:
        op.create_index("ix_activity_log_ms_product", "activity_log", [COLUMN])


def downgrade():
    op.drop_index("ix_activity_log_ms_product", table_name="activity_log")
    for table, name in ITEM_TABLES:
        _replace_check(table, name, OLD_TYPES)
    for table, fk_name, _ondelete in reversed(REFERENCES):
        foreign_keys = {item["name"] for item in sa.inspect(op.get_bind()).get_foreign_keys(table)}
        with op.batch_alter_table(table) as batch:
            if fk_name in foreign_keys:
                batch.drop_constraint(fk_name, type_="foreignkey")
            batch.drop_column(COLUMN)
    op.drop_table("master_sanitary_inventory")
    op.drop_table("master_sanitary_products")
