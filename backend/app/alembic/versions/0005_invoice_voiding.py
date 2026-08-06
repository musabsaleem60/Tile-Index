"""invoice voiding

Revision ID: 0005_invoice_voiding
Revises: 0004_desktop_statuses
Create Date: 2026-08-07
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_invoice_voiding"
down_revision = "0004_desktop_statuses"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("status", sa.String(length=20), nullable=False, server_default="active"))
    op.add_column("invoices", sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("invoices", sa.Column("voided_by_user_id", sa.Integer(), nullable=True))
    op.add_column("invoices", sa.Column("void_reason", sa.Text(), nullable=True))
    op.create_check_constraint("ck_invoices_status", "invoices", "status IN ('active', 'void')")
    op.create_foreign_key("fk_invoices_voided_by_user_id_users", "invoices", "users", ["voided_by_user_id"], ["id"], ondelete="SET NULL")

    op.add_column("invoice_items", sa.Column("boxes_from_boxes", sa.Integer(), nullable=True))
    op.add_column("invoice_items", sa.Column("pieces_from_loose", sa.Integer(), nullable=True))

    op.alter_column("stock_transactions", "product_id", existing_type=sa.Integer(), nullable=True)
    op.alter_column("stock_transactions", "grade", existing_type=sa.String(length=80), nullable=True)
    op.add_column("stock_transactions", sa.Column("accessory_id", sa.Integer(), nullable=True))
    op.add_column("stock_transactions", sa.Column("sanitary_product_id", sa.Integer(), nullable=True))
    op.add_column("stock_transactions", sa.Column("item_type", sa.String(length=30), nullable=False, server_default="tile"))
    op.add_column("stock_transactions", sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"))
    op.create_foreign_key("fk_stock_transactions_accessory_id_accessories", "stock_transactions", "accessories", ["accessory_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_stock_transactions_sanitary_product_id_sanitary_products", "stock_transactions", "sanitary_products", ["sanitary_product_id"], ["id"], ondelete="RESTRICT")


def downgrade() -> None:
    op.drop_constraint("fk_stock_transactions_sanitary_product_id_sanitary_products", "stock_transactions", type_="foreignkey")
    op.drop_constraint("fk_stock_transactions_accessory_id_accessories", "stock_transactions", type_="foreignkey")
    op.drop_column("stock_transactions", "quantity")
    op.drop_column("stock_transactions", "item_type")
    op.drop_column("stock_transactions", "sanitary_product_id")
    op.drop_column("stock_transactions", "accessory_id")
    op.alter_column("stock_transactions", "grade", existing_type=sa.String(length=80), nullable=False)
    op.alter_column("stock_transactions", "product_id", existing_type=sa.Integer(), nullable=False)

    op.drop_column("invoice_items", "pieces_from_loose")
    op.drop_column("invoice_items", "boxes_from_boxes")

    op.drop_constraint("fk_invoices_voided_by_user_id_users", "invoices", type_="foreignkey")
    op.drop_constraint("ck_invoices_status", "invoices", type_="check")
    op.drop_column("invoices", "void_reason")
    op.drop_column("invoices", "voided_by_user_id")
    op.drop_column("invoices", "voided_at")
    op.drop_column("invoices", "status")
