"""
Inventory Repository
Data access layer for inventory
"""

from database.init_db import get_connection
from models.inventory import Inventory


class InventoryRepository:
    """Repository for inventory operations"""
    
    @staticmethod
    def get_by_branch_product_grade(branch_id, product_id, grade):
        """Get inventory for specific branch, product, and grade"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, branch_id, product_id, grade, boxes, loose_pieces,
                   rate_per_sqm, rate_per_box, rate_per_piece, updated_at
            FROM inventory
            WHERE branch_id = ? AND product_id = ? AND grade = ?
        """, (branch_id, product_id, grade))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Inventory(id=row[0], branch_id=row[1], product_id=row[2], grade=row[3],
                           boxes=row[4], loose_pieces=row[5], rate_per_sqm=row[6],
                           rate_per_box=row[7], rate_per_piece=row[8], updated_at=row[9])
        return None
    
    @staticmethod
    def get_all_by_branch(branch_id):
        """Get all inventory for a branch"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, branch_id, product_id, grade, boxes, loose_pieces,
                   rate_per_sqm, rate_per_box, rate_per_piece, updated_at
            FROM inventory
            WHERE branch_id = ?
            ORDER BY product_id, grade
        """, (branch_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [Inventory(id=r[0], branch_id=r[1], product_id=r[2], grade=r[3],
                        boxes=r[4], loose_pieces=r[5], rate_per_sqm=r[6],
                        rate_per_box=r[7], rate_per_piece=r[8], updated_at=r[9]) for r in rows]
    
    @staticmethod
    def create_or_update(inventory):
        """Create or update inventory record"""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Check if exists
        existing = InventoryRepository.get_by_branch_product_grade(
            inventory.branch_id, inventory.product_id, inventory.grade
        )
        
        if existing:
            # Update
            cursor.execute("""
                UPDATE inventory SET
                    boxes = ?, loose_pieces = ?, rate_per_sqm = ?,
                    rate_per_box = ?, rate_per_piece = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (inventory.boxes, inventory.loose_pieces, inventory.rate_per_sqm,
                  inventory.rate_per_box, inventory.rate_per_piece, existing.id))
            inventory.id = existing.id
        else:
            # Create
            cursor.execute("""
                INSERT INTO inventory (branch_id, product_id, grade, boxes, loose_pieces,
                                     rate_per_sqm, rate_per_box, rate_per_piece)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (inventory.branch_id, inventory.product_id, inventory.grade,
                  inventory.boxes, inventory.loose_pieces, inventory.rate_per_sqm,
                  inventory.rate_per_box, inventory.rate_per_piece))
            inventory.id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return inventory
    
    @staticmethod
    def update_stock(branch_id, product_id, grade, boxes_delta, pieces_delta):
        """Update stock (add or subtract)"""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get current stock
        inventory = InventoryRepository.get_by_branch_product_grade(branch_id, product_id, grade)
        
        if not inventory:
            raise ValueError(f"Inventory not found for branch {branch_id}, product {product_id}, grade {grade}")
        
        new_boxes = inventory.boxes + boxes_delta
        new_pieces = inventory.loose_pieces + pieces_delta
        
        # Normalize: convert excess pieces to boxes if possible
        from repositories.product_repository import ProductRepository
        product = ProductRepository.get_by_id(product_id)
        if product:
            # If we have enough pieces to make a box, convert them
            while new_pieces >= product.pieces_per_box and new_pieces > 0:
                new_boxes += 1
                new_pieces -= product.pieces_per_box
            
            # If pieces are negative, try to convert boxes to pieces
            while new_pieces < 0 and new_boxes > 0:
                new_boxes -= 1
                new_pieces += product.pieces_per_box
        
        # Check for negative stock
        if new_boxes < 0 or (new_boxes == 0 and new_pieces < 0):
            raise ValueError(f"Insufficient stock. Cannot have negative inventory.")
        
        # Update
        cursor.execute("""
            UPDATE inventory SET
                boxes = ?, loose_pieces = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_boxes, new_pieces, inventory.id))
        
        conn.commit()
        conn.close()
        
        inventory.boxes = new_boxes
        inventory.loose_pieces = new_pieces
        return inventory

