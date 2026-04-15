
import sqlite3
import os

def check_products():
    db_path = os.path.join('data', 'tile_index.db')
    if not os.path.exists(db_path):
        print("Database not found")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    print("Products:")
    for p in products:
        print(p)
    
    cursor.execute("SELECT * FROM branches")
    branches = cursor.fetchall()
    print("\nBranches:")
    for b in branches:
        print(b)
    
    conn.close()

if __name__ == "__main__":
    check_products()
