
import sqlite3
import os

def migrate_accessories():
    db_path = os.path.join(os.getcwd(), 'data', 'tile_index.db')
    if not os.path.exists(db_path):
        print("Database not found")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Migrating accessories table to support 'Floor Waste'...")
    
    try:
        # Check if we need to migrate
        cursor.execute("PRAGMA table_info(accessories)")
        # SQLite doesn't show check constraints in table_info clearly, 
        # so we'll just do the migration to be safe or check the SQL
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='accessories'")
        sql = cursor.fetchone()[0]
        
        if "'Floor Waste'" in sql:
            print("Accessories table already supports Floor Waste.")
        else:
            # 1. Rename old table
            cursor.execute("ALTER TABLE accessories RENAME TO accessories_old")
            
            # 2. Create new table with updated constraint
            cursor.execute("""
                CREATE TABLE accessories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL CHECK(category IN ('Grout', 'Bond', 'Floor Waste')),
                    company TEXT NOT NULL,
                    unit_price REAL NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, company)
                )
            """)
            
            # 3. Copy data
            cursor.execute("""
                INSERT INTO accessories (id, name, category, company, unit_price, created_at)
                SELECT id, name, category, company, unit_price, created_at
                FROM accessories_old
            """)
            
            # 4. Drop old table
            cursor.execute("DROP TABLE accessories_old")
            
            conn.commit()
            print("Migration successful")
            
        # 5. Now seed the new items
        new_items = [
            ('Floor Waste', 'Floor Waste', 'Heritage (Chrome)', 1700),
            ('Floor Waste', 'Floor Waste', 'Heritage (Black)', 2200),
            ('Floor Waste', 'Floor Waste', 'Heritage (White)', 1700),
        ]
        
        for name, cat, comp, price in new_items:
            cursor.execute("""
                INSERT OR IGNORE INTO accessories (name, category, company, unit_price)
                VALUES (?, ?, ?, ?)
            """, (name, cat, comp, price))
        
        conn.commit()
        print("Seeded Heritage Floor Waste items.")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_accessories()
