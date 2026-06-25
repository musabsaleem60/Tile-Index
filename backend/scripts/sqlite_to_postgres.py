"""
One-time migration helper from the existing SQLite database to PostgreSQL.

Run after Alembic migrations:
    cd backend
    python -m scripts.sqlite_to_postgres "../data/tile_index.db"

This script preserves IDs so existing invoice references remain valid.
"""

import sqlite3
import sys
from sqlalchemy import text
from app.db.session import SessionLocal


TABLES = [
    "branches",
    "users",
    "products",
    "inventory",
    "accessories",
    "accessories_inventory",
    "sanitary_products",
    "sanitary_inventory",
    "invoices",
    "invoice_items",
    "stock_transactions",
    "sanitary_stock_transactions",
    "activity_log",
]


def table_exists(sqlite_conn, table_name: str) -> bool:
    row = sqlite_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def get_rows(sqlite_conn, table_name: str):
    cursor = sqlite_conn.execute(f"SELECT * FROM {table_name}")
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def copy_table(sqlite_conn, pg_session, table_name: str):
    if not table_exists(sqlite_conn, table_name):
        print(f"Skipped missing table {table_name}")
        return

    rows = transform_rows(sqlite_conn, table_name, get_rows(sqlite_conn, table_name))
    if not rows:
        return

    columns = list(rows[0].keys())
    placeholders = ", ".join(f":{column}" for column in columns)
    column_sql = ", ".join(columns)
    statement = text(f"INSERT INTO {table_name} ({column_sql}) VALUES ({placeholders}) ON CONFLICT DO NOTHING")

    for row in rows:
        pg_session.execute(statement, row)
    print(f"Copied {len(rows)} rows from {table_name}")


def transform_rows(sqlite_conn, table_name: str, rows: list[dict]) -> list[dict]:
    if table_name == "users":
        for row in rows:
            row["is_active"] = bool(row.get("is_active"))
        return rows

    if table_name == "invoice_items":
        return transform_invoice_items(sqlite_conn, rows)

    return rows


def transform_invoice_items(sqlite_conn, rows: list[dict]) -> list[dict]:
    products = {}
    if table_exists(sqlite_conn, "products"):
        products = {row["id"]: row for row in get_rows(sqlite_conn, "products")}

    accessories = {}
    if table_exists(sqlite_conn, "accessories"):
        accessories = {row["id"]: row for row in get_rows(sqlite_conn, "accessories")}

    sanitary_products = {}
    if table_exists(sqlite_conn, "sanitary_products"):
        sanitary_products = {row["id"]: row for row in get_rows(sqlite_conn, "sanitary_products")}

    transformed = []
    for row in rows:
        product_id = row.get("product_id")
        accessory_id = row.get("accessory_id")
        sanitary_product_id = row.get("sanitary_product_id")

        if product_id:
            product = products.get(product_id, {})
            item_type = "tile"
            description = f"{product.get('name', 'Tile')} - {row.get('tile_size') or product.get('tile_size', '')}".strip(" -")
            quantity = 0
            unit_price = 0
        elif accessory_id:
            accessory = accessories.get(accessory_id, {})
            item_type = "accessory"
            description = f"{accessory.get('name', 'Accessory')} ({accessory.get('company', '')})".strip()
            quantity = row.get("boxes") or 0
            unit_price = row.get("rate_per_box") or 0
        elif sanitary_product_id:
            sanitary = sanitary_products.get(sanitary_product_id, {})
            item_type = "sanitary"
            description = f"{sanitary.get('company_name', 'Sanitary')} - {sanitary.get('product_category', '')}".strip(" -")
            quantity = row.get("boxes") or 0
            unit_price = row.get("rate_per_box") or 0
        else:
            item_type = "accessory"
            description = "Migrated invoice item"
            quantity = row.get("boxes") or 0
            unit_price = row.get("rate_per_box") or 0

        row.setdefault("sanitary_product_id", None)
        row["item_type"] = item_type
        row["description"] = description or "Migrated invoice item"
        row["quantity"] = quantity
        row["unit_price"] = unit_price
        transformed.append(row)

    return transformed


def reset_sequences(pg_session):
    sequence_tables = [
        "branches",
        "users",
        "products",
        "inventory",
        "accessories",
        "accessories_inventory",
        "sanitary_products",
        "sanitary_inventory",
        "invoices",
        "invoice_items",
        "stock_transactions",
        "sanitary_stock_transactions",
        "activity_log",
    ]
    for table_name in sequence_tables:
        pg_session.execute(text(
            f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {table_name}), 1), true)"
        ))


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m scripts.sqlite_to_postgres path/to/tile_index.db")

    sqlite_path = sys.argv[1]
    sqlite_conn = sqlite3.connect(sqlite_path)
    pg_session = SessionLocal()
    try:
        for table in TABLES:
            copy_table(sqlite_conn, pg_session, table)
        reset_sequences(pg_session)
        pg_session.commit()
    except Exception:
        pg_session.rollback()
        raise
    finally:
        sqlite_conn.close()
        pg_session.close()


if __name__ == "__main__":
    main()
