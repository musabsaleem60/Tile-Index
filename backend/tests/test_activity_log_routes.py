import os
import unittest


os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "activity-route-order-test"

from app.api.activity_log import router  # noqa: E402


class ActivityLogRouteOrderTests(unittest.TestCase):
    def test_named_routes_precede_numeric_activity_route(self):
        paths = [route.path for route in router.routes]
        numeric_index = paths.index("/activity-log/{activity_id}")
        for path in (
            "/activity-log/actions",
            "/activity-log/products",
            "/activity-log/product-history/{product_id}",
        ):
            self.assertLess(paths.index(path), numeric_index, path)


if __name__ == "__main__":
    unittest.main()
