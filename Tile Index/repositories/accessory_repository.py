"""
Accessory Repository
Data access layer for accessories (grouts, bonds)
"""

from database.init_db import get_connection
from models.accessory import Accessory, AccessoryInventory


class AccessoryRepository:
    """Repository for accessory operations"""
    
    @staticmethod
    def get_all():
        """Get all accessories"""
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
        existing = AccessoryInventoryRepository.get_by_branch_accessory(branch_id, accessory_id)
        current_qty = existing.quantity if existing else 0
        new_qty = current_qty + quantity_to_add
        return AccessoryInventoryRepository.create_or_update(branch_id, accessory_id, new_qty)
    
    @staticmethod
    def deduct_stock(branch_id, accessory_id, quantity_to_deduct):
        """Deduct stock quantity"""
        existing = AccessoryInventoryRepository.get_by_branch_accessory(branch_id, accessory_id)
        if not existing:
            raise ValueError("No stock available for this accessory")
        
        new_qty = existing.quantity - quantity_to_deduct
        if new_qty < 0:
            raise ValueError(f"Insufficient stock. Available: {existing.quantity}, Requested: {quantity_to_deduct}")
        
        return AccessoryInventoryRepository.create_or_update(branch_id, accessory_id, new_qty)
