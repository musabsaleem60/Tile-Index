"""
Accessory Repository
Data access layer for accessories (grouts, bonds)
"""

from database.init_db import get_connection
from models.accessory import Accessory, AccessoryInventory
from desktop_client.remote_state import is_api_authenticated
from desktop_client.session import api_client, get_cached, set_cached, invalidate_cache


class AccessoryRepository:
    """Repository for accessory operations"""
    
    @staticmethod
    def get_all():
        """Get all accessories"""
        if is_api_authenticated():
            cached = get_cached("accessories")
            if cached is not None:
                return cached
            rows = api_client.get("/catalog/accessories")
            return set_cached("accessories", [
                Accessory(
                    id=r["id"],
                    name=r["name"],
                    category=r["category"],
                    company=r["company"],
                    unit_price=r["unit_price"],
                    created_at=r.get("created_at")
                )
                for r in rows
            ])

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category, company, unit_price, created_at FROM accessories ORDER BY category, company")
        rows = cursor.fetchall()
        conn.close()
        
        return [Accessory(id=r[0], name=r[1], category=r[2], company=r[3],
                          unit_price=r[4], created_at=r[5]) for r in rows]
    
    @staticmethod
    def get_by_category(category):
        """Get all accessories by category (Grout or Bond)"""
        if is_api_authenticated():
            return [a for a in AccessoryRepository.get_all() if a.category == category]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category, company, unit_price, created_at FROM accessories WHERE category = ? ORDER BY company", (category,))
        rows = cursor.fetchall()
        conn.close()
        
        return [Accessory(id=r[0], name=r[1], category=r[2], company=r[3],
                          unit_price=r[4], created_at=r[5]) for r in rows]
    
    @staticmethod
    def get_by_id(accessory_id):
        """Get accessory by ID"""
        if is_api_authenticated():
            for accessory in AccessoryRepository.get_all():
                if accessory.id == accessory_id:
                    return accessory
            return None

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category, company, unit_price, created_at FROM accessories WHERE id = ?", (accessory_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Accessory(id=row[0], name=row[1], category=row[2], company=row[3],
                             unit_price=row[4], created_at=row[5])
        return None
    
    @staticmethod
    def create(accessory):
        """Create a new accessory"""
        if is_api_authenticated():
            data = api_client.post("/catalog/accessories", {
                "name": accessory.name,
                "category": accessory.category,
                "company": accessory.company,
                "unit_price": accessory.unit_price,
            })
            invalidate_cache("accessories")
            return Accessory(id=data["id"], name=data["name"], category=data["category"],
                             company=data["company"], unit_price=data["unit_price"],
                             created_at=data.get("created_at"))

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO accessories (name, category, company, unit_price)
            VALUES (?, ?, ?, ?)
        """, (accessory.name, accessory.category, accessory.company, accessory.unit_price))
        accessory.id = cursor.lastrowid
        conn.commit()
        conn.close()
        return accessory
    
    @staticmethod
    def update(accessory):
        """Update an existing accessory"""
        if is_api_authenticated():
            data = api_client.put(f"/catalog/accessories/{accessory.id}", {
                "name": accessory.name,
                "category": accessory.category,
                "company": accessory.company,
                "unit_price": accessory.unit_price,
            })
            invalidate_cache("accessories")
            return Accessory(id=data["id"], name=data["name"], category=data["category"],
                             company=data["company"], unit_price=data["unit_price"],
                             created_at=data.get("created_at"))

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE accessories SET name = ?, category = ?, company = ?, unit_price = ?
            WHERE id = ?
        """, (accessory.name, accessory.category, accessory.company, accessory.unit_price, accessory.id))
        conn.commit()
        conn.close()
        return accessory
    
    @staticmethod
    def delete(accessory_id):
        """Delete an accessory"""
        if is_api_authenticated():
            api_client.delete(f"/catalog/accessories/{accessory_id}")
            invalidate_cache("accessories")
            return

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM accessories WHERE id = ?", (accessory_id,))
        conn.commit()
        conn.close()


class AccessoryInventoryRepository:
    """Repository for accessory inventory operations"""
    
    @staticmethod
    def get_by_branch_accessory(branch_id, accessory_id):
        """Get inventory for a specific branch and accessory"""
        if is_api_authenticated():
            rows = api_client.get(f"/inventory/accessories/{branch_id}")
            for r in rows:
                if r["accessory_id"] == accessory_id:
                    return AccessoryInventory(
                        id=r["id"],
                        branch_id=r["branch_id"],
                        accessory_id=r["accessory_id"],
                        quantity=r["quantity"],
                        updated_at=r.get("updated_at")
                    )
            return None

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, branch_id, accessory_id, quantity, updated_at
            FROM accessories_inventory
            WHERE branch_id = ? AND accessory_id = ?
        """, (branch_id, accessory_id))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return AccessoryInventory(id=row[0], branch_id=row[1], accessory_id=row[2],
                                       quantity=row[3], updated_at=row[4])
        return None
    
    @staticmethod
    def get_all_by_branch(branch_id):
        """Get all accessory inventory for a branch"""
        if is_api_authenticated():
            rows = api_client.get(f"/inventory/accessories/{branch_id}")
            results = []
            accessories = {a.id: a for a in AccessoryRepository.get_all()}
            for r in rows:
                inv = AccessoryInventory(id=r["id"], branch_id=r["branch_id"],
                                         accessory_id=r["accessory_id"], quantity=r["quantity"],
                                         updated_at=r.get("updated_at"))
                accessory = accessories.get(inv.accessory_id)
                if accessory:
                    inv.accessory_name = accessory.name
                    inv.accessory_category = accessory.category
                    inv.accessory_company = accessory.company
                    inv.accessory_unit_price = accessory.unit_price
                results.append(inv)
            return results

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ai.id, ai.branch_id, ai.accessory_id, ai.quantity, ai.updated_at,
                   a.name, a.category, a.company, a.unit_price
            FROM accessories_inventory ai
            JOIN accessories a ON ai.accessory_id = a.id
            WHERE ai.branch_id = ?
            ORDER BY a.category, a.company
        """, (branch_id,))
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for r in rows:
            inv = AccessoryInventory(id=r[0], branch_id=r[1], accessory_id=r[2],
                                      quantity=r[3], updated_at=r[4])
            # Attach accessory info
            inv.accessory_name = r[5]
            inv.accessory_category = r[6]
            inv.accessory_company = r[7]
            inv.accessory_unit_price = r[8]
            results.append(inv)
        return results
    
    @staticmethod
    def create_or_update(branch_id, accessory_id, quantity):
        """Create or update accessory inventory"""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if exists
        existing = AccessoryInventoryRepository.get_by_branch_accessory(branch_id, accessory_id)
        
        if existing:
            cursor.execute("""
                UPDATE accessories_inventory SET quantity = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (quantity, existing.id))
            existing.quantity = quantity
            result = existing
        else:
            cursor.execute("""
                INSERT INTO accessories_inventory (branch_id, accessory_id, quantity)
                VALUES (?, ?, ?)
            """, (branch_id, accessory_id, quantity))
            result = AccessoryInventory(
                id=cursor.lastrowid,
                branch_id=branch_id,
                accessory_id=accessory_id,
                quantity=quantity
            )
        
        conn.commit()
        conn.close()
        return result
    
    @staticmethod
    def add_stock(branch_id, accessory_id, quantity_to_add):
        """Add stock quantity"""
        if is_api_authenticated():
            data = api_client.post(f"/inventory/accessories/{accessory_id}/stock-in", {
                "branch_id": branch_id,
                "quantity": quantity_to_add,
                "notes": "Desktop accessory stock in",
            })
            return AccessoryInventory(id=data["id"], branch_id=data["branch_id"],
                                      accessory_id=data["accessory_id"], quantity=data["quantity"],
                                      updated_at=data.get("updated_at"))

        existing = AccessoryInventoryRepository.get_by_branch_accessory(branch_id, accessory_id)
        current_qty = existing.quantity if existing else 0
        new_qty = current_qty + quantity_to_add
        return AccessoryInventoryRepository.create_or_update(branch_id, accessory_id, new_qty)
    
    @staticmethod
    def deduct_stock(branch_id, accessory_id, quantity_to_deduct):
        """Deduct stock quantity"""
        if is_api_authenticated():
            data = api_client.post(f"/inventory/accessories/{accessory_id}/stock-out", {
                "branch_id": branch_id,
                "quantity": quantity_to_deduct,
                "notes": "Desktop accessory stock out",
            })
            return AccessoryInventory(id=data["id"], branch_id=data["branch_id"],
                                      accessory_id=data["accessory_id"], quantity=data["quantity"],
                                      updated_at=data.get("updated_at"))

        existing = AccessoryInventoryRepository.get_by_branch_accessory(branch_id, accessory_id)
        if not existing:
            raise ValueError("No stock available for this accessory")
        
        new_qty = existing.quantity - quantity_to_deduct
        if new_qty < 0:
            raise ValueError(f"Insufficient stock. Available: {existing.quantity}, Requested: {quantity_to_deduct}")
        
        return AccessoryInventoryRepository.create_or_update(branch_id, accessory_id, new_qty)
