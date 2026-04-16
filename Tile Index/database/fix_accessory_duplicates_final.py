
import sqlite3
import os

def migrate_and_cleanup():
    db_path = os.path.join(os.getcwd(), 'data', 'tile_index.db')
    if not os.path.exists(db_path):
        print("Database not found")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Applying professional cleanup and schema fix...")
    
    try:
        # 1. Create a temporary table with the UNIQUE constraint
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accessories_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL CHECK(category IN ('Grout', 'Bond', 'Floor Waste')),
                company TEXT NOT NULL,
                unit_price REAL NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, company)
            )
        """)
        
        # 2. Copy unique records from old to new
        cursor.execute("""
            INSERT OR IGNORE INTO accessories_new (name, category, company, unit_price, created_at)
            SELECT name, category, company, unit_price, created_at
            FROM accessories
            GROUP BY category, company
        """)
        
        # 3. Handle foreign keys in accessories_inventory and invoice_items
        # First, mapping of old IDs to new IDs
        cursor.execute("SELECT a.id, anew.id FROM accessories a JOIN accessories_new anew ON a.category = anew.category AND a.company = anew.company")
        id_map = cursor.fetchall()
        
        for old_id, new_id in id_map:
            if old_id != new_id:
                cursor.execute("UPDATE accessories_inventory SET accessory_id = ? WHERE accessory_id = ?", (new_id, old_id))
                cursor.execute("UPDATE invoice_items SET accessory_id = ? WHERE accessory_id = ?", (new_id, old_id))
        
        # 4. Drop old table and rename new one
        cursor.execute("DROP TABLE accessories")
        cursor.execute("ALTER TABLE accessories_new RENAME TO accessories")
        
        conn.commit()
        print("Database schema updated with UNIQUE constraint. Duplicates are now permanently blocked.")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_and_cleanup()
