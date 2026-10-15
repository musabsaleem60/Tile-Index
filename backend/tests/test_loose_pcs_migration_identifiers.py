"""Catch PostgreSQL identifier limits before deploying the Loose Pcs migration."""

import ast
import importlib
import unittest
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import AddConstraint, CreateTable


migration = importlib.import_module("app.alembic.versions.0014_loose_pcs")


class LoosePcsMigrationIdentifiersTests(unittest.TestCase):
    def test_postgres_foreign_key_ddl_and_identifier_lengths(self):
        source = Path(migration.__file__).read_text(encoding="utf-8")
        explicit_names = {
            node.value
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.startswith(("fk_", "ck_", "uq_", "ix_"))
        }
        foreign_keys = {name for name in explicit_names if name.startswith("fk_")}
        self.assertEqual(foreign_keys, set(migration.REFERENCE_FKS.values()) | {
            "fk_loose_pcs_inventory_branch_id_branches",
            "fk_loose_pcs_inventory_product_id_loose_pcs_products",
        })

        dialect = postgresql.dialect()
        for name in explicit_names | {"loose_pcs_products", "loose_pcs_inventory"}:
            dialect.validate_identifier(name)

        metadata = sa.MetaData()
        sa.Table("branches", metadata, sa.Column("id", sa.Integer, primary_key=True))
        sa.Table("loose_pcs_products", metadata, sa.Column("id", sa.Integer, primary_key=True))
        inventory = sa.Table(
            "loose_pcs_inventory", metadata,
            sa.Column("branch_id", sa.Integer, sa.ForeignKey(
                "branches.id", name="fk_loose_pcs_inventory_branch_id_branches")),
            sa.Column("product_id", sa.Integer, sa.ForeignKey(
                "loose_pcs_products.id", name="fk_loose_pcs_inventory_product_id_loose_pcs_products")),
        )
        create_ddl = str(CreateTable(inventory).compile(dialect=dialect))
        for name in foreign_keys - set(migration.REFERENCE_FKS.values()):
            self.assertIn(name, create_ddl)

        for table_name, name in migration.REFERENCE_FKS.items():
            table = sa.Table(table_name, metadata, sa.Column("loose_pcs_product_id", sa.Integer))
            constraint = sa.ForeignKeyConstraint(
                ["loose_pcs_product_id"], ["loose_pcs_products.id"], name=name,
            )
            table.append_constraint(constraint)
            self.assertIn(name, str(AddConstraint(constraint).compile(dialect=dialect)))


if __name__ == "__main__":
    unittest.main()
