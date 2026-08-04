"""tile excel schema foundation

Revision ID: 0002_tile_excel_schema
Revises: 0001_initial_schema
Create Date: 2026-08-04
"""

from __future__ import annotations

import re

from alembic import op
import sqlalchemy as sa


revision = "0002_tile_excel_schema"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


GRADE_MAP = {
    "Grade 1 (Prime)": "G1 Prime",
    "Grade 2 (Standard)": "G2 Standard",
    "Grade 3 (Regular)": "G3 Regular",
    "G1": "G1 Prime",
    "G2": "G2 Standard",
    "G3": "G3 Regular",
}

REVERSE_GRADE_MAP = {
    "G1 Prime": "Grade 1 (Prime)",
    "G2 Standard": "Grade 2 (Standard)",
    "G3 Regular": "Grade 3 (Regular)",
}

CANONICAL_GRADES = ("G1 Prime", "G2 Standard", "G3 Regular")
IMPORT_ROW_STATUSES = ("created", "updated", "stock_in", "stock_out", "skipped", "warning", "error", "blocked")


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    _create_foundation_tables()
    _add_product_columns()
    _backfill_products(bind)
    _add_product_uniqueness(dialect)
    _backfill_tile_sizes(bind)
    _migrate_grade_values(bind, GRADE_MAP)
    _add_stock_transaction_import_columns()
    _add_indexes()


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    _drop_index_if_exists("ix_stock_transactions_import_batch_id")
    _drop_index_if_exists("ix_import_batch_rows_batch_id")
    _drop_index_if_exists("ix_import_batches_file_hash")
    _drop_index_if_exists("ix_products_item_code")
    _drop_index_if_exists("ix_products_normalized_name_size")

    _migrate_grade_values(bind, REVERSE_GRADE_MAP, allowed_extra=set(GRADE_MAP.keys()))

    if dialect != "sqlite":
        _drop_constraint_if_exists("stock_transactions", "fk_stock_transactions_import_batch")
        _drop_constraint_if_exists("products", "uq_products_normalized_name_size")
        _drop_constraint_if_exists("products", "uq_products_item_code")

    _drop_column_if_exists("stock_transactions", "source_row_number")
    _drop_column_if_exists("stock_transactions", "import_batch_id")
    _drop_column_if_exists("products", "active")
    _drop_column_if_exists("products", "normalized_product_name")
    _drop_column_if_exists("products", "item_code")

    for table_name in (
        "import_batch_rows",
        "import_batches",
        "product_rate_overrides",
        "tile_rates",
        "tile_sizes",
        "branch_aliases",
    ):
        if _table_exists(table_name):
            op.drop_table(table_name)


def _create_foundation_tables():
    if not _table_exists("branch_aliases"):
        op.create_table(
            "branch_aliases",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id", ondelete="CASCADE"), nullable=False),
            sa.Column("alias_name", sa.String(120), nullable=False, unique=True),
            sa.Column("source_name", sa.String(120)),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if not _table_exists("tile_sizes"):
        op.create_table(
            "tile_sizes",
            sa.Column("tile_size", sa.String(80), primary_key=True),
            sa.Column("pieces_per_box", sa.Integer(), nullable=False),
            sa.Column("area_per_box", sa.Float(), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )

    if not _table_exists("tile_rates"):
        op.create_table(
            "tile_rates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("tile_size", sa.String(80), sa.ForeignKey("tile_sizes.tile_size", ondelete="RESTRICT"), nullable=False),
            sa.Column("grade", sa.String(80), nullable=False),
            sa.Column("rate_per_meter", sa.Float(), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.CheckConstraint("grade IN ('G1 Prime', 'G2 Standard', 'G3 Regular')", name="ck_tile_rates_grade"),
            sa.UniqueConstraint("tile_size", "grade", name="uq_tile_rates_size_grade"),
        )

    if not _table_exists("product_rate_overrides"):
        op.create_table(
            "product_rate_overrides",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
            sa.Column("grade", sa.String(80), nullable=False),
            sa.Column("rate_per_meter", sa.Float(), nullable=False),
            sa.Column("reason", sa.Text()),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.CheckConstraint("grade IN ('G1 Prime', 'G2 Standard', 'G3 Regular')", name="ck_product_rate_overrides_grade"),
            sa.UniqueConstraint("product_id", "grade", name="uq_product_rate_overrides_product_grade"),
        )

    if not _table_exists("import_batches"):
        op.create_table(
            "import_batches",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("batch_number", sa.String(40), nullable=False, unique=True),
            sa.Column("import_type", sa.String(40), nullable=False),
            sa.Column("file_name", sa.String(255), nullable=False),
            sa.Column("file_hash", sa.String(128), nullable=False),
            sa.Column("status", sa.String(40), nullable=False),
            sa.Column("exported_at", sa.DateTime(timezone=True)),
            sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("committed_at", sa.DateTime(timezone=True)),
            sa.Column("failed_at", sa.DateTime(timezone=True)),
            sa.Column("reverted_at", sa.DateTime(timezone=True)),
            sa.Column("summary_json", sa.JSON()),
            sa.Column("error_json", sa.JSON()),
            sa.CheckConstraint("import_type IN ('tiles')", name="ck_import_batches_type"),
            sa.CheckConstraint("status IN ('dry_run', 'committed', 'failed', 'reverted')", name="ck_import_batches_status"),
        )

    if not _table_exists("import_batch_rows"):
        op.create_table(
            "import_batch_rows",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("batch_id", sa.Integer(), sa.ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False),
            sa.Column("sheet_name", sa.String(120), nullable=False),
            sa.Column("row_number", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(40), nullable=False),
            sa.Column("operation", sa.String(40)),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="SET NULL")),
            sa.Column("item_code", sa.String(40)),
            sa.Column("branch_id", sa.Integer(), sa.ForeignKey("branches.id", ondelete="SET NULL")),
            sa.Column("grade", sa.String(80)),
            sa.Column("message", sa.Text()),
            sa.Column("before_json", sa.JSON()),
            sa.Column("after_json", sa.JSON()),
            sa.Column("created_transaction_id", sa.Integer(), sa.ForeignKey("stock_transactions.id", ondelete="SET NULL")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.CheckConstraint(
                "status IN ('created', 'updated', 'stock_in', 'stock_out', 'skipped', 'warning', 'error', 'blocked')",
                name="ck_import_batch_rows_status",
            ),
        )


def _add_product_columns():
    if not _column_exists("products", "item_code"):
        op.add_column("products", sa.Column("item_code", sa.String(40)))
    if not _column_exists("products", "normalized_product_name"):
        op.add_column("products", sa.Column("normalized_product_name", sa.String(160)))
    if not _column_exists("products", "active"):
        op.add_column("products", sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()))


def _backfill_products(bind):
    products = bind.execute(sa.text("SELECT id, name, tile_size FROM products ORDER BY id")).mappings().all()
    for product in products:
        bind.execute(
            sa.text(
                """
                UPDATE products
                SET item_code = COALESCE(NULLIF(TRIM(item_code), ''), :item_code),
                    normalized_product_name = COALESCE(NULLIF(TRIM(normalized_product_name), ''), :normalized_name)
                WHERE id = :id
                """
            ),
            {
                "id": product["id"],
                "item_code": f"TIL-{product['id']:06d}",
                "normalized_name": _normalize_product_name(product["name"]),
            },
        )

    duplicates = bind.execute(
        sa.text(
            """
            SELECT normalized_product_name, tile_size, COUNT(*) AS row_count
            FROM products
            GROUP BY normalized_product_name, tile_size
            HAVING COUNT(*) > 1
            """
        )
    ).mappings().all()
    if duplicates:
        detail = "; ".join(
            f"{row['normalized_product_name']} / {row['tile_size']} ({row['row_count']})"
            for row in duplicates
        )
        raise RuntimeError(f"Cannot add products normalized-name uniqueness: duplicate group(s): {detail}")


def _add_product_uniqueness(dialect: str):
    if dialect == "sqlite":
        _create_unique_index_if_missing("ix_products_item_code", "products", ["item_code"])
        _create_unique_index_if_missing("ix_products_normalized_name_size", "products", ["normalized_product_name", "tile_size"])
        return

    if not _constraint_exists("products", "uq_products_item_code"):
        op.create_unique_constraint("uq_products_item_code", "products", ["item_code"])
    if not _constraint_exists("products", "uq_products_normalized_name_size"):
        op.create_unique_constraint("uq_products_normalized_name_size", "products", ["normalized_product_name", "tile_size"])


def _backfill_tile_sizes(bind):
    conflicts = bind.execute(
        sa.text(
            """
            SELECT tile_size, COUNT(DISTINCT pieces_per_box) AS pieces_options,
                   COUNT(DISTINCT area_per_box) AS area_options
            FROM products
            GROUP BY tile_size
            HAVING COUNT(DISTINCT pieces_per_box) > 1 OR COUNT(DISTINCT area_per_box) > 1
            """
        )
    ).mappings().all()
    if conflicts:
        detail = "; ".join(
            f"{row['tile_size']} ({row['pieces_options']} pieces values, {row['area_options']} area values)"
            for row in conflicts
        )
        print(f"Skipped tile_sizes backfill for conflicting legacy size facts: {detail}")

    sizes = bind.execute(
        sa.text(
            """
            SELECT tile_size, MAX(pieces_per_box) AS pieces_per_box, MAX(area_per_box) AS area_per_box
            FROM products
            GROUP BY tile_size
            HAVING COUNT(DISTINCT pieces_per_box) = 1 AND COUNT(DISTINCT area_per_box) = 1
            """
        )
    ).mappings().all()
    for size in sizes:
        exists = bind.execute(
            sa.text("SELECT COUNT(*) FROM tile_sizes WHERE tile_size = :tile_size"),
            {"tile_size": size["tile_size"]},
        ).scalar_one()
        if not exists:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO tile_sizes (tile_size, pieces_per_box, area_per_box, active)
                    VALUES (:tile_size, :pieces_per_box, :area_per_box, :active)
                    """
                ),
                {**dict(size), "active": True},
            )


def _migrate_grade_values(bind, grade_map: dict[str, str], allowed_extra: set[str] | None = None):
    if bind.dialect.name == "sqlite":
        _migrate_grade_values_sqlite(bind, grade_map, allowed_extra)
        return

    allowed_extra = allowed_extra or set()
    allowed = set(grade_map) | set(grade_map.values()) | allowed_extra
    for table_name in ("inventory", "stock_transactions", "invoice_items"):
        if not _table_exists(table_name) or not _column_exists(table_name, "grade"):
            continue
        values = [
            row[0]
            for row in bind.execute(sa.text(f"SELECT DISTINCT grade FROM {table_name} WHERE grade IS NOT NULL")).all()
        ]
        unmapped = sorted(value for value in values if value not in allowed)
        if unmapped:
            raise RuntimeError(f"Unmapped grade value(s) in {table_name}.grade: {', '.join(unmapped)}")
        for old, new in grade_map.items():
            bind.execute(
                sa.text(f"UPDATE {table_name} SET grade = :new WHERE grade = :old"),
                {"old": old, "new": new},
            )


def _migrate_grade_values_sqlite(bind, grade_map: dict[str, str], allowed_extra: set[str] | None = None):
    allowed_extra = allowed_extra or set()
    allowed = set(grade_map) | set(grade_map.values()) | allowed_extra
    for table_name in ("inventory", "stock_transactions", "invoice_items"):
        if not _table_exists(table_name) or not _column_exists(table_name, "grade"):
            continue
        values = [
            row[0]
            for row in bind.execute(sa.text(f"SELECT DISTINCT grade FROM {table_name} WHERE grade IS NOT NULL")).all()
        ]
        unmapped = sorted(value for value in values if value not in allowed)
        if unmapped:
            raise RuntimeError(f"Unmapped grade value(s) in {table_name}.grade: {', '.join(unmapped)}")
        _sqlite_rebuild_table_with_grade_map(bind, table_name, grade_map)


def _sqlite_rebuild_table_with_grade_map(bind, table_name: str, grade_map: dict[str, str]):
    columns = bind.execute(sa.text(f"PRAGMA table_info({table_name})")).mappings().all()
    index_rows = bind.execute(
        sa.text(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type = 'index'
              AND tbl_name = :table_name
              AND sql IS NOT NULL
            """
        ),
        {"table_name": table_name},
    ).scalars().all()

    temp_table = f"{table_name}__grade_migration"
    column_sql = ", ".join(_sqlite_column_definition(column) for column in columns)
    bind.execute(sa.text("PRAGMA foreign_keys=OFF"))
    bind.execute(sa.text(f"DROP TABLE IF EXISTS {temp_table}"))
    bind.execute(sa.text(f"CREATE TABLE {temp_table} ({column_sql})"))

    column_names = [column["name"] for column in columns]
    source_select = []
    params = {}
    for column_name in column_names:
        if column_name == "grade":
            case_parts = []
            for index, (old, new) in enumerate(grade_map.items()):
                old_param = f"old_grade_{index}"
                new_param = f"new_grade_{index}"
                params[old_param] = old
                params[new_param] = new
                case_parts.append(f"WHEN grade = :{old_param} THEN :{new_param}")
            source_select.append(f"CASE {' '.join(case_parts)} ELSE grade END AS grade")
        else:
            source_select.append(_quote_identifier(column_name))

    quoted_columns = ", ".join(_quote_identifier(column_name) for column_name in column_names)
    bind.execute(
        sa.text(
            f"""
            INSERT INTO {temp_table} ({quoted_columns})
            SELECT {', '.join(source_select)}
            FROM {table_name}
            """
        ),
        params,
    )
    bind.execute(sa.text(f"DROP TABLE {table_name}"))
    bind.execute(sa.text(f"ALTER TABLE {temp_table} RENAME TO {table_name}"))
    for index_sql in index_rows:
        bind.execute(sa.text(index_sql))
    if table_name == "inventory":
        bind.execute(sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_inventory_branch_product_grade "
            "ON inventory(branch_id, product_id, grade)"
        ))
    bind.execute(sa.text("PRAGMA foreign_keys=ON"))


def _sqlite_column_definition(column) -> str:
    definition = f"{_quote_identifier(column['name'])} {column['type'] or 'TEXT'}"
    if column["pk"]:
        definition += " PRIMARY KEY"
    if column["notnull"] and not column["pk"]:
        definition += " NOT NULL"
    if column["dflt_value"] is not None:
        definition += f" DEFAULT {column['dflt_value']}"
    return definition


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _add_stock_transaction_import_columns():
    if not _column_exists("stock_transactions", "import_batch_id"):
        op.add_column("stock_transactions", sa.Column("import_batch_id", sa.Integer()))
    if not _column_exists("stock_transactions", "source_row_number"):
        op.add_column("stock_transactions", sa.Column("source_row_number", sa.Integer()))

    if op.get_bind().dialect.name != "sqlite" and not _constraint_exists("stock_transactions", "fk_stock_transactions_import_batch"):
        op.create_foreign_key(
            "fk_stock_transactions_import_batch",
            "stock_transactions",
            "import_batches",
            ["import_batch_id"],
            ["id"],
            ondelete="SET NULL",
        )


def _add_indexes():
    _create_index_if_missing("ix_import_batches_file_hash", "import_batches", ["file_hash"])
    _create_index_if_missing("ix_import_batch_rows_batch_id", "import_batch_rows", ["batch_id"])
    _create_index_if_missing("ix_stock_transactions_import_batch_id", "stock_transactions", ["import_batch_id"])


def _normalize_product_name(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _table_exists(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return any(column["name"] == column_name for column in sa.inspect(op.get_bind()).get_columns(table_name))


def _constraint_exists(table_name: str, constraint_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    constraints = inspector.get_unique_constraints(table_name) + inspector.get_foreign_keys(table_name)
    constraints += inspector.get_check_constraints(table_name)
    return any(constraint.get("name") == constraint_name for constraint in constraints)


def _index_exists(index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    for table_name in inspector.get_table_names():
        if any(index.get("name") == index_name for index in inspector.get_indexes(table_name)):
            return True
    return False


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]):
    if _table_exists(table_name) and not _index_exists(index_name):
        op.create_index(index_name, table_name, columns)


def _create_unique_index_if_missing(index_name: str, table_name: str, columns: list[str]):
    if _table_exists(table_name) and not _index_exists(index_name):
        op.create_index(index_name, table_name, columns, unique=True)


def _drop_index_if_exists(index_name: str):
    if _index_exists(index_name):
        op.drop_index(index_name)


def _drop_column_if_exists(table_name: str, column_name: str):
    if _column_exists(table_name, column_name):
        op.drop_column(table_name, column_name)


def _drop_constraint_if_exists(table_name: str, constraint_name: str):
    if _constraint_exists(table_name, constraint_name):
        op.drop_constraint(constraint_name, table_name)
