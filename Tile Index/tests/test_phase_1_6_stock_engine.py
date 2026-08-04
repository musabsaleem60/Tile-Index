import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DESKTOP = PROJECT_ROOT / "Tile Index"
BACKEND = PROJECT_ROOT / "backend"
sys.path.insert(0, str(DESKTOP))
sys.path.insert(0, str(BACKEND))


def assert_local_database_url(url):
    if not url:
        return
    normalized = url.lower()
    local_markers = (
        "sqlite://",
        "localhost",
        "127.0.0.1",
        "::1",
    )
    if not any(marker in normalized for marker in local_markers):
        raise RuntimeError(f"Refusing to run stock-engine tests against non-local DATABASE_URL: {url}")


def configure_backend_test_env(db_path):
    url = f"sqlite:///{db_path.as_posix()}"
    assert_local_database_url(url)
    os.environ["DATABASE_URL"] = url
    os.environ.setdefault("SECRET_KEY", "phase-1-6-test-secret")


class StockMathTests(unittest.TestCase):
    def test_sell_loose_borrows_from_boxes(self):
        from stock_math import deduct_verbatim_stock

        boxes, loose = deduct_verbatim_stock(3, 2, 0, 5, 12)

        self.assertEqual((boxes, loose), (2, 9))

    def test_box_order_can_be_fulfilled_from_loose_stock(self):
        from stock_math import deduct_verbatim_stock

        boxes, loose = deduct_verbatim_stock(0, 25, 2, 0, 12)

        self.assertEqual((boxes, loose), (0, 1))

    def test_box_order_preserves_surplus_loose_bucket_when_boxes_available(self):
        from stock_math import deduct_verbatim_stock

        boxes, loose = deduct_verbatim_stock(3, 25, 2, 0, 12)

        self.assertEqual((boxes, loose), (1, 25))

    def test_mixed_order_deducts_from_each_bucket_without_redistribution(self):
        from stock_math import deduct_verbatim_stock

        boxes, loose = deduct_verbatim_stock(3, 25, 1, 5, 12)

        self.assertEqual((boxes, loose), (2, 20))

    def test_box_plus_piece_order_can_be_fulfilled_from_loose_only_stock(self):
        from stock_math import deduct_verbatim_stock

        boxes, loose = deduct_verbatim_stock(0, 25, 1, 1, 12)

        self.assertEqual((boxes, loose), (0, 12))

    def test_insufficient_stock_is_blocked(self):
        from stock_math import deduct_verbatim_stock

        with self.assertRaises(ValueError):
            deduct_verbatim_stock(0, 23, 2, 0, 12)


class DesktopStockEngineTests(unittest.TestCase):
    def setUp(self):
        from desktop_client import session

        session.current_token = None
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "scratch_tile_index.db"
        self._install_desktop_scratch_db()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _install_desktop_scratch_db(self):
        import database.init_db as init_db
        import repositories.branch_repository as branch_repository
        import repositories.inventory_repository as inventory_repository
        import repositories.product_repository as product_repository
        import repositories.stock_transaction_repository as stock_transaction_repository
        import repositories.user_repository as user_repository

        def scratch_path():
            return str(self.db_path)

        init_db.get_db_path = scratch_path
        for module in (
            branch_repository,
            inventory_repository,
            product_repository,
            stock_transaction_repository,
            user_repository,
        ):
            module.get_connection = init_db.get_connection

        init_db.init_database()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO products (name, tile_size, area_per_box, pieces_per_box)
                VALUES ('Round Trip Tile', '10x20', 1.53, 12)
                """
            )
            self.product_id = conn.execute("SELECT id FROM products WHERE name = 'Round Trip Tile'").fetchone()[0]
            self.branch_id = conn.execute("SELECT id FROM branches ORDER BY id LIMIT 1").fetchone()[0]
            conn.commit()
        finally:
            conn.close()

    def _stock(self):
        from repositories.inventory_repository import InventoryRepository
        from utils.grade_constants import GRADE_1

        return InventoryRepository.get_by_branch_product_grade(self.branch_id, self.product_id, GRADE_1)

    def test_stock_in_of_large_loose_count_stores_verbatim(self):
        from services.inventory_service import InventoryService
        from utils.grade_constants import GRADE_1

        InventoryService.add_stock(self.branch_id, self.product_id, GRADE_1, 0, 25, 100, 1530, 127.5)

        stock = self._stock()
        self.assertEqual((stock.boxes, stock.loose_pieces), (0, 25))

    def test_import_count_set_stores_verbatim(self):
        from models.inventory import Inventory
        from repositories.inventory_repository import InventoryRepository
        from utils.grade_constants import GRADE_1

        InventoryRepository.create_or_update(
            Inventory(
                branch_id=self.branch_id,
                product_id=self.product_id,
                grade=GRADE_1,
                boxes=0,
                loose_pieces=25,
                rate_per_sqm=0,
                rate_per_box=0,
                rate_per_piece=0,
            )
        )

        stock = self._stock()
        self.assertEqual((stock.boxes, stock.loose_pieces), (0, 25))

    def test_full_export_import_round_trip_numbers_are_identical(self):
        from models.inventory import Inventory
        from repositories.inventory_repository import InventoryRepository
        from utils.grade_constants import GRADE_1

        exported = {"boxes": 0, "loose_pieces": 25}
        InventoryRepository.create_or_update(
            Inventory(
                branch_id=self.branch_id,
                product_id=self.product_id,
                grade=GRADE_1,
                boxes=exported["boxes"],
                loose_pieces=exported["loose_pieces"],
                rate_per_sqm=0,
                rate_per_box=0,
                rate_per_piece=0,
            )
        )
        imported = self._stock()
        re_exported = {"boxes": imported.boxes, "loose_pieces": imported.loose_pieces}

        self.assertEqual(re_exported, exported)

    def test_desktop_invoice_deduction_borrows_loose_from_boxes(self):
        from models.inventory import Inventory
        from repositories.inventory_repository import InventoryRepository
        from services.inventory_service import InventoryService
        from utils.grade_constants import GRADE_1

        InventoryRepository.create_or_update(
                Inventory(
                    branch_id=self.branch_id,
                    product_id=self.product_id,
                    grade=GRADE_1,
                    boxes=3,
                    loose_pieces=2,
                    rate_per_sqm=100,
                    rate_per_box=1200,
                    rate_per_piece=100,
                )
        )

        InventoryService.deduct_stock(self.branch_id, self.product_id, GRADE_1, 0, 5)

        stock = self._stock()
        self.assertEqual((stock.boxes, stock.loose_pieces), (2, 9))


class BackendStockEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "backend_stock.db"
        configure_backend_test_env(self.db_path)

        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.models import Base
        from app.models.entities import Branch, Inventory, Product, User

        self.engine = create_engine(os.environ["DATABASE_URL"], future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        self.db = self.Session()
        self.branch = Branch(name="Test Branch", code="TB")
        self.user = User(username="tester", password_hash="x", role="admin", is_active=True)
        self.product = Product(name="Backend Tile", tile_size="10x20", area_per_box=1.53, pieces_per_box=12)
        self.db.add_all([self.branch, self.user, self.product])
        self.db.commit()
        self.db.refresh(self.branch)
        self.db.refresh(self.user)
        self.db.refresh(self.product)
        self.Inventory = Inventory

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_backend_stock_in_stores_loose_verbatim(self):
        from app.api.inventory import tile_stock_in
        from app.schemas.common import StockInRequest

        payload = StockInRequest(
            branch_id=self.branch.id,
            product_id=self.product.id,
            grade="G1 Prime",
            boxes=0,
            loose_pieces=25,
            rate_per_sqm=0,
            rate_per_box=0,
            rate_per_piece=0,
        )

        stock = tile_stock_in(payload, db=self.db, current_user=self.user)

        self.assertEqual((stock.boxes, stock.loose_pieces), (0, 25))

    def test_backend_box_order_can_be_fulfilled_from_loose_stock(self):
        from app.services.invoices import _build_tile_item

        stock = self.Inventory(
            branch_id=self.branch.id,
            product_id=self.product.id,
            grade="G1 Prime",
            boxes=0,
            loose_pieces=25,
            rate_per_sqm=0,
            rate_per_box=1200,
            rate_per_piece=100,
        )
        self.db.add(stock)
        self.db.commit()

        item = _build_tile_item(
            self.db,
            self.branch.id,
            SimpleNamespace(product_id=self.product.id, grade="G1 Prime", boxes=2, loose_pieces=0),
            self.user,
        )

        self.assertEqual((stock.boxes, stock.loose_pieces), (0, 1))
        self.assertEqual((item.boxes, item.loose_pieces), (2, 0))


if __name__ == "__main__":
    unittest.main()
