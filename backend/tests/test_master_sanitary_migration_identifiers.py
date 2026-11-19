"""Validate all new Master Sanitary identifiers under PostgreSQL rules."""

import ast
import importlib
import unittest
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import AddConstraint, CreateTable


migration = importlib.import_module("app.alembic.versions.0015_master_sanitary")


class MasterSanitaryMigrationIdentifiersTests(unittest.TestCase):
    def test_postgres_ddl_identifiers(self):
        source = Path(migration.__file__).read_text(encoding="utf-8")
        names = {
            node.value for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
            and node.value.startswith(("fk_", "ck_", "uq_", "ix_"))
        }
        expected_fks = {name for _table, name, _ondelete in migration.REFERENCES} | {
            "fk_ms_inventory_branch", "fk_ms_inventory_product",
        }
        self.assertEqual({name for name in names if name.startswith("fk_")}, expected_fks)
        dialect = postgresql.dialect()
        for name in names | {"master_sanitary_products", "master_sanitary_inventory", migration.COLUMN,
                             "master_sanitary_products_pkey", "master_sanitary_inventory_pkey"}:
            dialect.validate_identifier(name)
            self.assertLessEqual(len(name.encode("utf-8")), 63)

        metadata = sa.MetaData()
        sa.Table("branches", metadata, sa.Column("id", sa.Integer, primary_key=True))
        products = sa.Table(
            "master_sanitary_products", metadata,
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("normalized_name", sa.String(160)),
            sa.Column("normalized_color", sa.String(80)),
            sa.Column("sku", sa.String(40)),
            sa.UniqueConstraint("normalized_name", "normalized_color", name="uq_ms_product_identity"),
            sa.UniqueConstraint("sku", name="uq_ms_product_sku"),
        )
        product_ddl = str(CreateTable(products).compile(dialect=dialect))
        self.assertNotIn("price", product_ddl.lower())
        for name in ("uq_ms_product_identity", "uq_ms_product_sku"):
            self.assertIn(name, product_ddl)
        inventory = sa.Table(
            "master_sanitary_inventory", metadata,
            sa.Column("branch_id", sa.Integer, sa.ForeignKey("branches.id", name="fk_ms_inventory_branch")),
            sa.Column("product_id", sa.Integer, sa.ForeignKey("master_sanitary_products.id", name="fk_ms_inventory_product")),
            sa.Column("quantity", sa.Integer),
            sa.Column("price", sa.Numeric(14, 2)),
            sa.UniqueConstraint("branch_id", "product_id", name="uq_ms_inventory_branch_product"),
            sa.CheckConstraint("quantity >= 0", name="ck_ms_inventory_quantity"),
            sa.CheckConstraint("price IS NULL OR price >= 0", name="ck_ms_inventory_price"),
        )
        ddl = str(CreateTable(inventory).compile(dialect=dialect))
        self.assertIn("price", ddl.lower())
        for name in ("fk_ms_inventory_branch", "fk_ms_inventory_product", "uq_ms_inventory_branch_product", "ck_ms_inventory_quantity", "ck_ms_inventory_price"):
            self.assertIn(name, ddl)
        for table_name, name, _ondelete in migration.REFERENCES:
            table = sa.Table(table_name, metadata, sa.Column(migration.COLUMN, sa.Integer))
            fk = sa.ForeignKeyConstraint([migration.COLUMN], ["master_sanitary_products.id"], name=name)
            table.append_constraint(fk)
            self.assertIn(name, str(AddConstraint(fk).compile(dialect=dialect)))


if __name__ == "__main__":
    unittest.main()
