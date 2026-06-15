"""
Sanitary Repository
Data access layer for sanitary products and inventory
"""

from database.init_db import get_connection
from models.sanitary import SanitaryProduct, SanitaryInventory
from desktop_client.remote_state import is_api_authenticated
from desktop_client.session import api_client, get_cached, set_cached, invalidate_cache


class SanitaryProductRepository:
    """Repository for sanitary product operations"""

    @staticmethod
    def get_all(company=None, product_category=None, color=None):
        """Get all sanitary products, optionally filtered"""
        if is_api_authenticated():
            cache_key = f"sanitary:{company or 'All'}:{product_category or 'All'}:{color or 'All'}"
            cached = get_cached(cache_key)
            if cached is not None:
                return cached
            params = []
            if company and company != 'All':
                params.append(f"company={company}")
            if product_category and product_category != 'All':
                params.append(f"category={product_category}")
            if color and color != 'All':
                params.append(f"color={color}")
            path = "/catalog/sanitary"
            if params:
                from urllib.parse import quote
                encoded = []
                for p in params:
                    key, value = p.split("=", 1)
                    encoded.append(f"{key}={quote(value)}")
                path += "?" + "&".join(encoded)
            rows = api_client.get(path)
            return set_cached(cache_key, [
                SanitaryProduct(
                    id=r["id"],
                    company_name=r["company_name"],
                    product_category=r["product_category"],
                    color=r["color"],
                    purchase_price=r["purchase_price"],
                    sale_price=r["sale_price"],
                    sku=r["sku"],
                    created_at=r.get("created_at")
                )
                for r in rows
            ])

        conn = get_connection()
        cursor = conn.cursor()

        query = """
            SELECT id, company_name, product_category, color, purchase_price,
                   sale_price, sku, created_at
            FROM sanitary_products
            WHERE 1=1
        """
        params = []

        if company and company != 'All':
            query += " AND company_name = ?"
            params.append(company)
        if product_category and product_category != 'All':
            query += " AND product_category = ?"
            params.append(product_category)
        if color and color != 'All':
            query += " AND color = ?"
            params.append(color)

        query += " ORDER BY company_name, product_category, color"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            SanitaryProduct(
                id=r[0], company_name=r[1], product_category=r[2], color=r[3],
                purchase_price=r[4], sale_price=r[5], sku=r[6], created_at=r[7]
            )
            for r in rows
        ]

    @staticmethod
    def get_by_id(sanitary_product_id):
        """Get sanitary product by ID"""
        if is_api_authenticated():
            for product in SanitaryProductRepository.get_all():
                if product.id == sanitary_product_id:
                    return product
            return None

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, company_name, product_category, color, purchase_price,
                   sale_price, sku, created_at
            FROM sanitary_products
            WHERE id = ?
        """, (sanitary_product_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return SanitaryProduct(
                id=row[0], company_name=row[1], product_category=row[2], color=row[3],
                purchase_price=row[4], sale_price=row[5], sku=row[6], created_at=row[7]
            )
        return None

    @staticmethod
    def create(product):
        """Create a new sanitary product"""
        if is_api_authenticated():
            data = api_client.post("/catalog/sanitary", {
                "company_name": product.company_name,
                "product_category": product.product_category,
                "color": product.color,
                "purchase_price": product.purchase_price,
                "sale_price": product.sale_price,
                "sku": product.sku,
            })
            invalidate_cache("sanitary")
            return SanitaryProduct(id=data["id"], company_name=data["company_name"],
                                   product_category=data["product_category"], color=data["color"],
                                   purchase_price=data["purchase_price"], sale_price=data["sale_price"],
                                   sku=data["sku"], created_at=data.get("created_at"))

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sanitary_products
                (company_name, product_category, color, purchase_price, sale_price, sku)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            product.company_name,
            product.product_category,
            product.color,
            product.purchase_price,
            product.sale_price,
            product.sku
        ))
        product.id = cursor.lastrowid
        conn.commit()
        conn.close()
        return product

    @staticmethod
    def update(product):
        """Update an existing sanitary product"""
        if is_api_authenticated():
            data = api_client.put(f"/catalog/sanitary/{product.id}", {
                "company_name": product.company_name,
                "product_category": product.product_category,
                "color": product.color,
                "purchase_price": product.purchase_price,
                "sale_price": product.sale_price,
                "sku": product.sku,
            })
            invalidate_cache("sanitary")
            return SanitaryProduct(id=data["id"], company_name=data["company_name"],
                                   product_category=data["product_category"], color=data["color"],
                                   purchase_price=data["purchase_price"], sale_price=data["sale_price"],
                                   sku=data["sku"], created_at=data.get("created_at"))

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sanitary_products
            SET company_name = ?, product_category = ?, color = ?,
                purchase_price = ?, sale_price = ?, sku = ?
            WHERE id = ?
        """, (
            product.company_name,
            product.product_category,
            product.color,
            product.purchase_price,
            product.sale_price,
            product.sku,
            product.id
        ))
        conn.commit()
        conn.close()
        return product

    @staticmethod
    def delete(sanitary_product_id):
        """Delete a sanitary product"""
        if is_api_authenticated():
            api_client.delete(f"/catalog/sanitary/{sanitary_product_id}")
            invalidate_cache("sanitary")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sanitary_products WHERE id = ?", (sanitary_product_id,))
        conn.commit()
        conn.close()


class SanitaryInventoryRepository:
    """Repository for sanitary inventory operations"""

    @staticmethod
    def get_by_branch_product(branch_id, sanitary_product_id):
        """Get inventory for a specific branch and sanitary product"""
        if is_api_authenticated():
            rows = api_client.get(f"/inventory/sanitary/{branch_id}")
            for r in rows:
                if r["sanitary_product_id"] == sanitary_product_id:
                    return SanitaryInventory(id=r["id"], branch_id=r["branch_id"],
                                             sanitary_product_id=r["sanitary_product_id"],
                                             quantity=r["quantity"], updated_at=r.get("updated_at"))
            return None

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, branch_id, sanitary_product_id, quantity, updated_at
            FROM sanitary_inventory
            WHERE branch_id = ? AND sanitary_product_id = ?
        """, (branch_id, sanitary_product_id))
        row = cursor.fetchone()
        conn.close()

        if row:
            return SanitaryInventory(
                id=row[0], branch_id=row[1], sanitary_product_id=row[2],
                quantity=row[3], updated_at=row[4]
            )
        return None

    @staticmethod
    def get_all_by_branch(branch_id, company=None, product_category=None, color=None):
        """Get all sanitary inventory for a branch, optionally filtered"""
        if is_api_authenticated():
            rows = api_client.get(f"/inventory/sanitary/{branch_id}")
            products = {
                p.id: p for p in SanitaryProductRepository.get_all(company, product_category, color)
            }
            results = []
            for r in rows:
                product = products.get(r["sanitary_product_id"])
                if not product:
                    continue
                inv = SanitaryInventory(id=r["id"], branch_id=r["branch_id"],
                                        sanitary_product_id=r["sanitary_product_id"],
                                        quantity=r["quantity"], updated_at=r.get("updated_at"))
                inv.company_name = product.company_name
                inv.product_category = product.product_category
                inv.color = product.color
                inv.purchase_price = product.purchase_price
                inv.sale_price = product.sale_price
                inv.sku = product.sku
                results.append(inv)
            return results

        conn = get_connection()
        cursor = conn.cursor()

        query = """
            SELECT si.id, si.branch_id, si.sanitary_product_id, si.quantity, si.updated_at,
                   sp.company_name, sp.product_category, sp.color, sp.purchase_price,
                   sp.sale_price, sp.sku
            FROM sanitary_inventory si
            JOIN sanitary_products sp ON si.sanitary_product_id = sp.id
            WHERE si.branch_id = ?
        """
        params = [branch_id]

        if company and company != 'All':
            query += " AND sp.company_name = ?"
            params.append(company)
        if product_category and product_category != 'All':
            query += " AND sp.product_category = ?"
            params.append(product_category)
        if color and color != 'All':
            query += " AND sp.color = ?"
            params.append(color)

        query += " ORDER BY sp.company_name, sp.product_category, sp.color"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for r in rows:
            inv = SanitaryInventory(
                id=r[0],
                branch_id=r[1],
                sanitary_product_id=r[2],
                quantity=r[3],
                updated_at=r[4]
            )
            inv.company_name = r[5]
            inv.product_category = r[6]
            inv.color = r[7]
            inv.purchase_price = r[8]
            inv.sale_price = r[9]
            inv.sku = r[10]
            results.append(inv)
        return results

    @staticmethod
    def create_or_update(branch_id, sanitary_product_id, quantity):
        """Create or update sanitary inventory"""
        conn = get_connection()
        cursor = conn.cursor()

        existing = SanitaryInventoryRepository.get_by_branch_product(branch_id, sanitary_product_id)

        if existing:
            cursor.execute("""
                UPDATE sanitary_inventory
                SET quantity = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (quantity, existing.id))
            existing.quantity = quantity
            result = existing
        else:
            cursor.execute("""
                INSERT INTO sanitary_inventory (branch_id, sanitary_product_id, quantity)
                VALUES (?, ?, ?)
            """, (branch_id, sanitary_product_id, quantity))
            result = SanitaryInventory(
                id=cursor.lastrowid,
                branch_id=branch_id,
                sanitary_product_id=sanitary_product_id,
                quantity=quantity
            )

        conn.commit()
        conn.close()
        return result

    @staticmethod
    def add_stock(branch_id, sanitary_product_id, quantity_to_add):
        """Add sanitary stock quantity"""
        if is_api_authenticated():
            data = api_client.post(f"/inventory/sanitary/{sanitary_product_id}/stock-in", {
                "branch_id": branch_id,
                "quantity": quantity_to_add,
                "notes": "Desktop sanitary stock in",
            })
            return SanitaryInventory(id=data["id"], branch_id=data["branch_id"],
                                     sanitary_product_id=data["sanitary_product_id"],
                                     quantity=data["quantity"], updated_at=data.get("updated_at"))

        existing = SanitaryInventoryRepository.get_by_branch_product(branch_id, sanitary_product_id)
        current_qty = existing.quantity if existing else 0
        return SanitaryInventoryRepository.create_or_update(
            branch_id, sanitary_product_id, current_qty + quantity_to_add
        )

    @staticmethod
    def deduct_stock(branch_id, sanitary_product_id, quantity_to_deduct):
        """Deduct sanitary stock quantity"""
        if is_api_authenticated():
            data = api_client.post(f"/inventory/sanitary/{sanitary_product_id}/stock-out", {
                "branch_id": branch_id,
                "quantity": quantity_to_deduct,
                "notes": "Desktop sanitary stock out",
            })
            return SanitaryInventory(id=data["id"], branch_id=data["branch_id"],
                                     sanitary_product_id=data["sanitary_product_id"],
                                     quantity=data["quantity"], updated_at=data.get("updated_at"))

        existing = SanitaryInventoryRepository.get_by_branch_product(branch_id, sanitary_product_id)
        if not existing:
            raise ValueError("No stock available for this sanitary product")

        new_qty = existing.quantity - quantity_to_deduct
        if new_qty < 0:
            raise ValueError(
                f"Insufficient stock. Available: {existing.quantity}, Requested: {quantity_to_deduct}"
            )

        return SanitaryInventoryRepository.create_or_update(branch_id, sanitary_product_id, new_qty)


class SanitaryStockTransactionRepository:
    """Repository for sanitary stock movement history"""

    @staticmethod
    def create(user_id, branch_id, sanitary_product_id, transaction_type, quantity, notes=None):
        """Create a sanitary stock transaction"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sanitary_stock_transactions
                (user_id, branch_id, sanitary_product_id, transaction_type, quantity, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, branch_id, sanitary_product_id, transaction_type, quantity, notes))
        transaction_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return transaction_id
