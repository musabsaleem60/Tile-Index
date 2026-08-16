"""invoice item source branch

Revision ID: 0006_invoice_item_source_branch
Revises: 0005_invoice_voiding
Create Date: 2026-08-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_invoice_item_source_branch"
down_revision = "0005_invoice_voiding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.add_column("invoice_items", sa.Column("source_branch_id", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE invoice_items
        SET source_branch_id = (
            SELECT invoices.branch_id
            FROM invoices
            WHERE invoices.id = invoice_items.invoice_id
        )
        WHERE source_branch_id IS NULL
        """
    )
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("invoice_items") as batch_op:
            batch_op.alter_column("source_branch_id", existing_type=sa.Integer(), nullable=False)
            batch_op.create_foreign_key(
                "fk_invoice_items_source_branch_id_branches",
                "branches",
                ["source_branch_id"],
                ["id"],
                ondelete="RESTRICT",
            )
    else:
        op.alter_column("invoice_items", "source_branch_id", existing_type=sa.Integer(), nullable=False)
        op.create_foreign_key(
            "fk_invoice_items_source_branch_id_branches",
            "invoice_items",
            "branches",
            ["source_branch_id"],
            ["id"],
            ondelete="RESTRICT",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("invoice_items") as batch_op:
            batch_op.drop_constraint("fk_invoice_items_source_branch_id_branches", type_="foreignkey")
            batch_op.drop_column("source_branch_id")
    else:
        op.drop_constraint("fk_invoice_items_source_branch_id_branches", "invoice_items", type_="foreignkey")
        op.drop_column("invoice_items", "source_branch_id")
