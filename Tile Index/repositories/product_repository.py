"""
Product Repository
Data access layer for products
"""

from database.init_db import get_connection
from models.product import Product


class ProductRepository:
    """Repository for product operations"""
    
    @staticmethod
    def get_all():
        """Get all products"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, tile_size, area_per_box, pieces_per_box, created_at FROM products ORDER BY name, tile_size")
        rows = cursor.fetchall()
        conn.close()
        
        return [Product(id=r[0], name=r[1], tile_size=r[2], area_per_box=r[3], 
                       pieces_per_box=r[4], created_at=r[5]) for r in rows]
    
    @staticmethod
    def get_by_id(product_id):
        """Get product by ID"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, tile_size, area_per_box, pieces_per_box, created_at FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Product(id=row[0], name=row[1], tile_size=row[2], area_per_box=row[3],
                          pieces_per_box=row[4], created_at=row[5])
        return None
    
    @staticmethod
    def create(product, user=None):
        """Create a new product"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO products (name, tile_size, area_per_box, pieces_per_box)
            VALUES (?, ?, ?, ?)
        """, (product.name, product.tile_size, product.area_per_box, product.pieces_per_box))
        product.id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Log activity
        if user:
            try:
                from services.activity_log_service import ActivityLogService
                ActivityLogService.log_product_added(user, product.name, product.tile_size)
            except:
                pass
        
        return product
    
    @staticmethod
    def update(product, user=None):
        """Update an existing product"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE products SET name = ?, tile_size = ?, area_per_box = ?, pieces_per_box = ?
            WHERE id = ?
        """, (product.name, product.tile_size, product.area_per_box, product.pieces_per_box, product.id))
        conn.commit()
        conn.close()
        
        # Log activity
        if user:
            try:
                from services.activity_log_service import ActivityLogService
                ActivityLogService.log_product_edited(user, product.name, product.tile_size)
            except:
                pass
        
        return product
    
    @staticmethod
    def delete(product_id, user=None):
        """Delete a product"""
        # Get product info before deletion for logging
        product = None
        if user:
            product = ProductRepository.get_by_id(product_id)
        
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        conn.close()
        
        # Log activity
        if user and product:
            try:
                from services.activity_log_service import ActivityLogService
                ActivityLogService.log_product_deleted(user, product.name, product.tile_size)
            except:
                pass

