"""product client codes

Revision ID: 0010_product_client_codes
Revises: 0009_invoice_remarks
Create Date: 2026-09-16
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_product_client_codes"
down_revision = "0009_invoice_remarks"
branch_labels = None
depends_on = None


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    if not _table_exists("product_client_codes"):
        op.create_table(
            "product_client_codes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("client_code", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        )
    if not _index_exists("product_client_codes", "ix_product_client_codes_product_id"):
        op.create_index("ix_product_client_codes_product_id", "product_client_codes", ["product_id"])
    if not _index_exists("product_client_codes", "ix_product_client_codes_client_code"):
        op.create_index("ix_product_client_codes_client_code", "product_client_codes", ["client_code"])


def downgrade() -> None:
    if _table_exists("product_client_codes"):
        if _index_exists("product_client_codes", "ix_product_client_codes_client_code"):
            op.drop_index("ix_product_client_codes_client_code", table_name="product_client_codes")
        if _index_exists("product_client_codes", "ix_product_client_codes_product_id"):
            op.drop_index("ix_product_client_codes_product_id", table_name="product_client_codes")
        op.drop_table("product_client_codes")
