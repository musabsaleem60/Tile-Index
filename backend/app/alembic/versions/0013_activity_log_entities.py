"""add structured activity log entity references

Revision ID: 0013_activity_log_entities
Revises: 0012_query_performance_indexes
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_activity_log_entities"
down_revision = "0012_query_performance_indexes"
branch_labels = None
depends_on = None


COLUMNS = (
    ("event_category", sa.String(length=30), None),
    ("product_id", sa.Integer(), "products"),
    ("accessory_id", sa.Integer(), "accessories"),
    ("sanitary_product_id", sa.Integer(), "sanitary_products"),
    ("invoice_id", sa.Integer(), "invoices"),
    ("return_id", sa.Integer(), "invoice_returns"),
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing = {column["name"] for column in inspector.get_columns("activity_log")}
    with op.batch_alter_table("activity_log") as batch:
        for name, type_, target in COLUMNS:
            if name not in existing:
                batch.add_column(sa.Column(name, type_, nullable=True))
                if target:
                    batch.create_foreign_key(
                        f"fk_activity_log_{name}_{target}", target,
                        [name], ["id"], ondelete="SET NULL",
                    )
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("activity_log")}
    for name, _type, _target in COLUMNS:
        index_name = f"ix_activity_log_{name}"
        if index_name not in indexes:
            op.create_index(index_name, "activity_log", [name])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("activity_log")}
    columns = {column["name"] for column in inspector.get_columns("activity_log")}
    for name, _type, _target in reversed(COLUMNS):
        index_name = f"ix_activity_log_{name}"
        if index_name in indexes:
            op.drop_index(index_name, table_name="activity_log")
    with op.batch_alter_table("activity_log") as batch:
        for name, _type, target in reversed(COLUMNS):
            if name in columns:
                if target:
                    batch.drop_constraint(f"fk_activity_log_{name}_{target}", type_="foreignkey")
                batch.drop_column(name)
