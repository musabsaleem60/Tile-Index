"""invoice payments

Revision ID: 0007_invoice_payments
Revises: 0006_invoice_item_source_branch
Create Date: 2026-09-01
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_invoice_payments"
down_revision = "0006_invoice_item_source_branch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("invoice_payments"):
        op.create_table(
            "invoice_payments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("invoice_id", sa.Integer(), nullable=False),
            sa.Column("branch_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("amount", sa.Numeric(), nullable=False),
            sa.Column("payment_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("method", sa.String(length=30), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
            sa.CheckConstraint("amount > 0", name="ck_invoice_payments_amount_positive"),
            sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], name="fk_invoice_payments_invoice_id_invoices", ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], name="fk_invoice_payments_branch_id_branches"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_invoice_payments_user_id_users"),
        )
    indexes = {index.get("name") for index in sa.inspect(op.get_bind()).get_indexes("invoice_payments")}
    if "idx_invoice_payments_invoice_id" not in indexes:
        op.create_index("idx_invoice_payments_invoice_id", "invoice_payments", ["invoice_id"])
    if "idx_invoice_payments_payment_date" not in indexes:
        op.create_index("idx_invoice_payments_payment_date", "invoice_payments", ["payment_date"])
    if "idx_invoice_payments_branch_id" not in indexes:
        op.create_index("idx_invoice_payments_branch_id", "invoice_payments", ["branch_id"])


def downgrade() -> None:
    op.drop_index("idx_invoice_payments_branch_id", table_name="invoice_payments")
    op.drop_index("idx_invoice_payments_payment_date", table_name="invoice_payments")
    op.drop_index("idx_invoice_payments_invoice_id", table_name="invoice_payments")
    op.drop_table("invoice_payments")
