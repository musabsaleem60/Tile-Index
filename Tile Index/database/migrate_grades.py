"""
Grade Migration Script
Migrates existing grade data from G1/G2/G3 to new format
Run this once to update existing database
"""

import sqlite3
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.init_db import get_db_path


def migrate_grades_internal(cursor, conn):
    """Internal migration function called from init_db"""
    # Check if old grade values exist in any table
    old_grades_exist = False
    for table in ['inventory', 'invoice_items', 'stock_transactions']:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE grade IN ('G1', 'G2', 'G3')")
            count = cursor.fetchone()[0]
            if count > 0:
                old_grades_exist = True
                break
        except sqlite3.OperationalError:
            # Table doesn't exist yet, skip
            pass
    
    if not old_grades_exist:
        return  # No migration needed
    
    # Disable foreign key constraints temporarily
    cursor.execute("PRAGMA foreign_keys = OFF")
    
    try:
        # Check if old grades exist
        cursor.execute("SELECT COUNT(*) FROM inventory WHERE grade IN ('G1', 'G2', 'G3')")
        inv_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM invoice_items WHERE grade IN ('G1', 'G2', 'G3')")
        inv_item_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM stock_transactions WHERE grade IN ('G1', 'G2', 'G3')")
        trans_count = cursor.fetchone()[0]
        
        total = inv_count + inv_item_count + trans_count
        
        if total == 0:
            print("No old grade data found. Migration not needed.")
            return
        
        print(f"Found {total} records with old grade format. Migrating...")
        
        # Recreate tables with new constraints
        # First, drop and recreate inventory table
        print("Migrating inventory table...")
        cursor.execute("""
            CREATE TABLE inventory_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                branch_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                grade TEXT NOT NULL CHECK(grade IN ('Grade 1 (Prime)', 'Grade 2 (Standard)', 'Grade 3 (Regular)')),
                boxes INTEGER NOT NULL DEFAULT 0,
                loose_pieces INTEGER NOT NULL DEFAULT 0,
                rate_per_sqm REAL NOT NULL,
                rate_per_box REAL NOT NULL,
                rate_per_piece REAL NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
                UNIQUE(branch_id, product_id, grade)
            )
        """)
        
        cursor.execute("""
            INSERT INTO inventory_new 
            SELECT id, branch_id, product_id,
                   CASE grade
                       WHEN 'G1' THEN 'Grade 1 (Prime)'
                       WHEN 'G2' THEN 'Grade 2 (Standard)'
                       WHEN 'G3' THEN 'Grade 3 (Regular)'
                       ELSE grade
                   END as grade,
                   boxes, loose_pieces, rate_per_sqm, rate_per_box, rate_per_piece, updated_at
            FROM inventory
        """)
        
        cursor.execute("DROP TABLE inventory")
        cursor.execute("ALTER TABLE inventory_new RENAME TO inventory")
        
        # Recreate invoice_items table
        print("Migrating invoice_items table...")
        cursor.execute("""
            CREATE TABLE invoice_items_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                tile_size TEXT NOT NULL,
                grade TEXT NOT NULL CHECK(grade IN ('Grade 1 (Prime)', 'Grade 2 (Standard)', 'Grade 3 (Regular)')),
                boxes INTEGER NOT NULL DEFAULT 0,
                loose_pieces INTEGER NOT NULL DEFAULT 0,
                rate_per_sqm REAL NOT NULL,
                rate_per_box REAL NOT NULL,
                rate_per_piece REAL NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
            )
        """)
        
        cursor.execute("""
            INSERT INTO invoice_items_new 
            SELECT id, invoice_id, product_id, tile_size,
                   CASE grade
                       WHEN 'G1' THEN 'Grade 1 (Prime)'
                       WHEN 'G2' THEN 'Grade 2 (Standard)'
                       WHEN 'G3' THEN 'Grade 3 (Regular)'
                       ELSE grade
                   END as grade,
                   boxes, loose_pieces, rate_per_sqm, rate_per_box, rate_per_piece, line_total
            FROM invoice_items
        """)
        
        cursor.execute("DROP TABLE invoice_items")
        cursor.execute("ALTER TABLE invoice_items_new RENAME TO invoice_items")
        
        # Recreate stock_transactions table
        print("Migrating stock_transactions table...")
        cursor.execute("""
            CREATE TABLE stock_transactions_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                branch_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                grade TEXT NOT NULL CHECK(grade IN ('Grade 1 (Prime)', 'Grade 2 (Standard)', 'Grade 3 (Regular)')),
                transaction_type TEXT NOT NULL CHECK(transaction_type IN ('IN', 'OUT')),
                boxes INTEGER NOT NULL DEFAULT 0,
                loose_pieces INTEGER NOT NULL DEFAULT 0,
                transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
                FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
            )
        """)
        
        cursor.execute("""
            INSERT INTO stock_transactions_new 
            SELECT id, user_id, branch_id, product_id,
                   CASE grade
                       WHEN 'G1' THEN 'Grade 1 (Prime)'
                       WHEN 'G2' THEN 'Grade 2 (Standard)'
                       WHEN 'G3' THEN 'Grade 3 (Regular)'
                       ELSE grade
                   END as grade,
                   transaction_type, boxes, loose_pieces, transaction_date, notes
            FROM stock_transactions
        """)
        
        cursor.execute("DROP TABLE stock_transactions")
        cursor.execute("ALTER TABLE stock_transactions_new RENAME TO stock_transactions")
        
        # Recreate indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_branch_product_grade ON inventory(branch_id, product_id, grade)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_transactions_user ON stock_transactions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_transactions_date ON stock_transactions(transaction_date)")
        
        conn.commit()
        print(f"✓ Migration completed successfully! {total} records updated.")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        cursor.execute("PRAGMA foreign_keys = ON")


def migrate_grades():
    """Standalone migration function for command-line use"""
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print("Database not found. Nothing to migrate.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        migrate_grades_internal(cursor, conn)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Grade Migration Script")
    print("=" * 60)
    migrate_grades()
    print("=" * 60)

