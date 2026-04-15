
import sqlite3
import os

def migrate_grout_colors():
    db_path = os.path.join(os.getcwd(), 'data', 'tile_index.db')
    if not os.path.exists(db_path):
        print("Database not found")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("Adding color variants for Shabir and Strong Grouts...")
    
    try:
        # 1. Categories already support 'Grout'
        
        # 2. Add Shabir Grout variants (Price assumed 400 as per previous seed)
        shabir_colors = [
            "White", "Almond", "Brown", "Marble Beige", "Sky Blue", 
            "Inca Gold", "Smoke Grey", "Slate Grey", "Dark Grey", 
            "Dark Brown", "Midnight Black"
        ]
        
        for color in shabir_colors:
            cursor.execute("""
                INSERT OR IGNORE INTO accessories (name, category, company, unit_price)
                VALUES (?, ?, ?, ?)
            """, ("Grout", "Grout", f"Shabir ({color})", 400))
            
        # 3. Add Strong Grout variants (Price assumed 250 as per previous seed)
        strong_colors = [
            "White", "Ivory", "Light Grey", "Dark Grey", "Light Brown", 
            "Dark Brown", "Black", "Sky Blue", "Sage"
        ]
        
        for color in strong_colors:
            cursor.execute("""
                INSERT OR IGNORE INTO accessories (name, category, company, unit_price)
                VALUES (?, ?, ?, ?)
            """, ("Grout", "Grout", f"Strong ({color})", 250))
            
        # 4. Remove the generic entries if they exist
        cursor.execute("DELETE FROM accessories WHERE company = 'Shabir' AND category = 'Grout'")
        cursor.execute("DELETE FROM accessories WHERE company = 'Strong' AND category = 'Grout'")
        
        conn.commit()
        print(f"Successfully added {len(shabir_colors)} Shabir and {len(strong_colors)} Strong grout variants.")
        
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_grout_colors()
