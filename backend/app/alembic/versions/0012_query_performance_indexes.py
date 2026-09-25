"""add indexes for stock and invoice query performance

Revision ID: 0012_query_performance_indexes
Revises: 0011_invoice_returns
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_query_performance_indexes"
down_revision = "0011_invoice_returns"
branch_labels = None
depends_on = None


INDEXES = (
    ("ix_invoices_invoice_date", "invoices", ["invoice_date"]),
    ("ix_invoices_status_invoice_date", "invoices", ["status", "invoice_date"]),
    ("ix_invoices_branch_status_invoice_date", "invoices", ["branch_id", "status", "invoice_date"]),
    ("ix_inventory_product_grade_branch", "inventory", ["product_id", "grade", "branch_id"]),
    ("ix_accessories_inventory_accessory_branch", "accessories_inventory", ["accessory_id", "branch_id"]),
    ("ix_sanitary_inventory_product_branch", "sanitary_inventory", ["sanitary_product_id", "branch_id"]),
    ("ix_invoice_items_invoice_id", "invoice_items", ["invoice_id"]),
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for name, table, columns in INDEXES:
        existing = {index["name"] for index in inspector.get_indexes(table)}
        if name not in existing:
            op.create_index(name, table, columns)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for name, table, _columns in reversed(INDEXES):
        existing = {index["name"] for index in inspector.get_indexes(table)}
        if name in existing:
            op.drop_index(name, table_name=table)
