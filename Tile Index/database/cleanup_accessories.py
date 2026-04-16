
import sqlite3
import os

def check_and_cleanup():
    db_path = os.path.join(os.getcwd(), 'data', 'tile_index.db')
    if not os.path.exists(db_path):
        print("Database not found")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check duplicates
    print("Checking for duplicate accessories...")
    cursor.execute("""
        SELECT category, company, COUNT(*) 
        FROM accessories 
        GROUP BY category, company 
        HAVING COUNT(*) > 1
    """)
    duplicates = cursor.fetchall()
    
    if not duplicates:
        print("No duplicates found in database.")
    else:
        print(f"Found {len(duplicates)} groups of duplicates.")
        for cat, comp, count in duplicates:
            print(f"- {cat} / {comp}: {count} times")
            
            # Keep the one with the lowest ID, delete others
            cursor.execute("""
                DELETE FROM accessories 
                WHERE id NOT IN (
                    SELECT MIN(id) 
                    FROM accessories 
                    GROUP BY category, company
                )
                AND category = ? AND company = ?
            """, (cat, comp))
        
        conn.commit()
        print("Duplicates cleaned up.")
    
    conn.close()

if __name__ == "__main__":
    check_and_cleanup()
