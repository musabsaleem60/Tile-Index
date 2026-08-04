
import sqlite3
import os

def migrate_invoice_items():
    db_path = os.path.join(os.getcwd(), 'data', 'tile_index.db')
    if not os.path.exists(db_path):
        print("Database not found")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Migrating invoice_items table...")
    
    try:
        # 1. Rename old table
        cursor.execute("ALTER TABLE invoice_items RENAME TO invoice_items_old")
        
        # 2. Create new table with relaxed constraints
        cursor.execute("""
            CREATE TABLE invoice_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER NOT NULL,
                product_id INTEGER,
                accessory_id INTEGER,
                tile_size TEXT,
                grade TEXT CHECK(grade IS NULL OR grade IN ('Grade 1 (Prime)', 'Grade 2 (Standard)', 'Grade 3 (Regular)')),
                boxes INTEGER DEFAULT 0,
                loose_pieces INTEGER DEFAULT 0,
                rate_per_sqm REAL DEFAULT 0,
                rate_per_box REAL DEFAULT 0,
                rate_per_piece REAL DEFAULT 0,
                line_total REAL NOT NULL,
                FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
                FOREIGN KEY (accessory_id) REFERENCES accessories(id) ON DELETE RESTRICT
            )
        """)
        
        # 3. Copy data
        # Note: We assume accessory_id was recently added and is NULL for all old items
        cursor.execute("""
            INSERT INTO invoice_items (id, invoice_id, product_id, tile_size, grade, boxes, loose_pieces, 
                                     rate_per_sqm, rate_per_box, rate_per_piece, line_total)
            SELECT id, invoice_id, product_id, tile_size, grade, boxes, loose_pieces, 
                   rate_per_sqm, rate_per_box, rate_per_piece, line_total
            FROM invoice_items_old
        """)
        
        # 4. Drop old table
        cursor.execute("DROP TABLE invoice_items_old")
        
        conn.commit()
        print("Migration successful")
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_invoice_items()
