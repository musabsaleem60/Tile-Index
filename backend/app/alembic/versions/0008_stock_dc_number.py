"""stock transaction dc number

Revision ID: 0008_stock_dc_number
Revises: 0007_invoice_payments
Create Date: 2026-09-02
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_stock_dc_number"
down_revision = "0007_invoice_payments"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in sa.inspect(op.get_bind()).get_columns(table_name))


def _index_exists(table_name: str, index_name: str) -> bool:
    return any(index["name"] == index_name for index in sa.inspect(op.get_bind()).get_indexes(table_name))


def upgrade() -> None:
    if not _column_exists("stock_transactions", "dc_number"):
        op.add_column("stock_transactions", sa.Column("dc_number", sa.String(length=80), nullable=True))
    if not _index_exists("stock_transactions", "idx_stock_transactions_dc_number"):
        op.create_index("idx_stock_transactions_dc_number", "stock_transactions", ["dc_number"])


def downgrade() -> None:
    if _index_exists("stock_transactions", "idx_stock_transactions_dc_number"):
        op.drop_index("idx_stock_transactions_dc_number", table_name="stock_transactions")
    if _column_exists("stock_transactions", "dc_number"):
        op.drop_column("stock_transactions", "dc_number")
