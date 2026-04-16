
import sqlite3
import os

def migrate_spacers():
    db_path = os.path.join(os.getcwd(), 'data', 'tile_index.db')
    if not os.path.exists(db_path):
        print("Database not found")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Migrating database for Spacers...")
    
    try:
        # 1. Update the table to support 'Spacer' in CHECK constraint
        # SQLite doesn't allow altering CHECK constraints, so we use the Recreate Table pattern
        cursor.execute("PRAGMA foreign_keys=OFF")
        
        cursor.execute("""
            CREATE TABLE accessories_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL CHECK(category IN ('Grout', 'Bond', 'Floor Waste', 'Spacer')),
                company TEXT NOT NULL,
                unit_price REAL NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, company)
            )
        """)
        
        cursor.execute("""
            INSERT INTO accessories_new (id, name, category, company, unit_price, created_at)
            SELECT id, name, category, company, unit_price, created_at FROM accessories
        """)
        
        cursor.execute("DROP TABLE accessories")
        cursor.execute("ALTER TABLE accessories_new RENAME TO accessories")
        
        # 2. Add Spacer Variants
        spacers = [
            ('Wall Spacer (1mm)', 'Spacer', 'Wall Spacer (1mm)', 100),
            ('Wall Spacer (1.5mm)', 'Spacer', 'Wall Spacer (1.5mm)', 100),
            ('Wall Spacer (2mm)', 'Spacer', 'Wall Spacer (2mm)', 100),
            ('Wall Spacer (3mm)', 'Spacer', 'Wall Spacer (3mm)', 100),
            ('Wall Spacer (4mm)', 'Spacer', 'Wall Spacer (4mm)', 100),
            ('Wall Spacer (5mm)', 'Spacer', 'Wall Spacer (5mm)', 100),
            ('Floor Spacer Male', 'Spacer', 'Floor Spacer Male (Standard)', 300),
            ('Floor Spacer Female (1mm)', 'Spacer', 'Floor Spacer Female (1mm)', 300),
            ('Floor Spacer Female (1.5mm)', 'Spacer', 'Floor Spacer Female (1.5mm)', 300),
            ('Floor Spacer Female (2mm)', 'Spacer', 'Floor Spacer Female (2mm)', 300),
            ('Floor Spacer Female (3mm)', 'Spacer', 'Floor Spacer Female (3mm)', 300),
            ('Floor Spacer Female (4mm)', 'Spacer', 'Floor Spacer Female (4mm)', 300),
            ('Floor Spacer Female (5mm)', 'Spacer', 'Floor Spacer Female (5mm)', 300),
        ]
        
        cursor.executemany("""
            INSERT OR IGNORE INTO accessories (name, category, company, unit_price) 
            VALUES (?, ?, ?, ?)
        """, spacers)
        
        cursor.execute("PRAGMA foreign_keys=ON")
        conn.commit()
        print(f"Migration successful. Added {len(spacers)} spacer variants.")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_spacers()
