"""invoice remarks

Revision ID: 0009_invoice_remarks
Revises: 0008_stock_dc_number
Create Date: 2026-09-05
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_invoice_remarks"
down_revision = "0008_stock_dc_number"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in sa.inspect(op.get_bind()).get_columns(table_name))


def upgrade() -> None:
    if not _column_exists("invoices", "remarks"):
        op.add_column("invoices", sa.Column("remarks", sa.Text(), nullable=True))


def downgrade() -> None:
    if _column_exists("invoices", "remarks"):
        op.drop_column("invoices", "remarks")
