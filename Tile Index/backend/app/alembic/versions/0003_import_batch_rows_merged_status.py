"""Allow merged import batch row status.

Revision ID: 0003_import_merged_status
Revises: 0002_tile_excel_schema
Create Date: 2026-08-04
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_import_merged_status"
down_revision = "0002_tile_excel_schema"
branch_labels = None
depends_on = None


OLD_STATUSES = "'created', 'updated', 'stock_in', 'stock_out', 'skipped', 'warning', 'error', 'blocked'"
NEW_STATUSES = f"{OLD_STATUSES}, 'merged'"


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "import_batch_rows",
            recreate="always",
            table_args=(
                sa.CheckConstraint(f"status IN ({NEW_STATUSES})", name="ck_import_batch_rows_status"),
            ),
        ):
            pass
        return

    op.drop_constraint("ck_import_batch_rows_status", "import_batch_rows", type_="check")
    op.create_check_constraint(
        "ck_import_batch_rows_status",
        "import_batch_rows",
        f"status IN ({NEW_STATUSES})",
    )


def downgrade():
    bind = op.get_bind()
    merged_count = bind.execute(sa.text("SELECT COUNT(*) FROM import_batch_rows WHERE status = 'merged'")).scalar() or 0
    if merged_count:
        raise RuntimeError("Cannot downgrade while import_batch_rows contains merged statuses")

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "import_batch_rows",
            recreate="always",
            table_args=(
                sa.CheckConstraint(f"status IN ({OLD_STATUSES})", name="ck_import_batch_rows_status"),
            ),
        ):
            pass
        return

    op.drop_constraint("ck_import_batch_rows_status", "import_batch_rows", type_="check")
    op.create_check_constraint(
        "ck_import_batch_rows_status",
        "import_batch_rows",
        f"status IN ({OLD_STATUSES})",
    )
