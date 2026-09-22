"""invoice returns and exchanges

Revision ID: 0011_invoice_returns
Revises: 0010_product_client_codes
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_invoice_returns"
down_revision = "0010_product_client_codes"
branch_labels = None
depends_on = None


def _table_exists(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _ensure_index(table: str, name: str, columns: list[str]) -> None:
    indexes = {row["name"] for row in sa.inspect(op.get_bind()).get_indexes(table)}
    if name not in indexes:
        op.create_index(name, table, columns)


def upgrade() -> None:
    # 0001 uses metadata.create_all(), so a brand-new test database already
    # contains models added by later revisions. Production upgrades do not.
    if _table_exists("invoice_returns"):
        _ensure_index("invoice_returns", "ix_invoice_returns_invoice_id", ["invoice_id"])
        _ensure_index("invoice_returns", "ix_invoice_returns_return_date", ["return_date"])
        _ensure_index("invoice_return_items", "ix_invoice_return_items_return_id", ["return_id"])
        _ensure_index("invoice_return_items", "ix_invoice_return_items_invoice_item_id", ["invoice_item_id"])
        _ensure_index("return_exchange_items", "ix_return_exchange_items_return_id", ["return_id"])
        _ensure_index("return_settlements", "ix_return_settlements_return_id", ["return_id"])
        return
    op.create_table(
        "invoice_returns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("return_number", sa.String(40), nullable=True),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("return_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("returned_value", sa.Numeric(14, 2), nullable=False),
        sa.Column("exchange_value", sa.Numeric(14, 2), nullable=False),
        sa.Column("difference_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.String(20), server_default="completed", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("return_number", name="uq_invoice_returns_number"),
        sa.CheckConstraint("status IN ('completed', 'void')", name="ck_invoice_returns_status"),
        sa.CheckConstraint("length(trim(reason)) >= 5", name="ck_invoice_returns_reason"),
    )
    op.create_index("ix_invoice_returns_invoice_id", "invoice_returns", ["invoice_id"])
    op.create_index("ix_invoice_returns_return_date", "invoice_returns", ["return_date"])

    op.create_table(
        "invoice_return_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("return_id", sa.Integer(), nullable=False),
        sa.Column("invoice_item_id", sa.Integer(), nullable=False),
        sa.Column("source_branch_id", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(30), nullable=False),
        sa.Column("boxes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("loose_pieces", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rate_per_sqm", sa.Numeric(14, 4), server_default="0", nullable=False),
        sa.Column("rate_per_box", sa.Numeric(14, 4), server_default="0", nullable=False),
        sa.Column("rate_per_piece", sa.Numeric(14, 4), server_default="0", nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 4), server_default="0", nullable=False),
        sa.Column("discounted_line_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("boxes_restored_to_boxes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pieces_restored_to_loose", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["return_id"], ["invoice_returns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_item_id"], ["invoice_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("item_type IN ('tile', 'accessory', 'sanitary')", name="ck_invoice_return_items_type"),
    )
    op.create_index("ix_invoice_return_items_return_id", "invoice_return_items", ["return_id"])
    op.create_index("ix_invoice_return_items_invoice_item_id", "invoice_return_items", ["invoice_item_id"])

    op.create_table(
        "return_exchange_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("return_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer()),
        sa.Column("accessory_id", sa.Integer()),
        sa.Column("sanitary_product_id", sa.Integer()),
        sa.Column("source_branch_id", sa.Integer(), nullable=False),
        sa.Column("item_type", sa.String(30), nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("tile_size", sa.String(80)),
        sa.Column("grade", sa.String(80)),
        sa.Column("boxes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("loose_pieces", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rate_per_sqm", sa.Numeric(14, 4), server_default="0", nullable=False),
        sa.Column("rate_per_box", sa.Numeric(14, 4), server_default="0", nullable=False),
        sa.Column("rate_per_piece", sa.Numeric(14, 4), server_default="0", nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 4), server_default="0", nullable=False),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("boxes_from_boxes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("pieces_from_loose", sa.Integer(), server_default="0", nullable=False),
        sa.ForeignKeyConstraint(["return_id"], ["invoice_returns.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["accessory_id"], ["accessories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["sanitary_product_id"], ["sanitary_products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("item_type IN ('tile', 'accessory', 'sanitary')", name="ck_return_exchange_items_type"),
    )
    op.create_index("ix_return_exchange_items_return_id", "return_exchange_items", ["return_id"])

    op.create_table(
        "return_settlements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("return_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=False),
        sa.Column("direction", sa.String(30), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("method", sa.String(30)),
        sa.Column("settlement_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["return_id"], ["invoice_returns.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("amount > 0", name="ck_return_settlements_amount"),
        sa.CheckConstraint("direction IN ('refund_to_customer', 'payment_from_customer')", name="ck_return_settlements_direction"),
    )
    op.create_index("ix_return_settlements_return_id", "return_settlements", ["return_id"])


def downgrade() -> None:
    op.drop_table("return_settlements")
    op.drop_table("return_exchange_items")
    op.drop_table("invoice_return_items")
    op.drop_table("invoice_returns")
