
import sqlite3
import os

def print_db_structure():
    db_path = os.path.join(os.getcwd(), 'data', 'tile_index.db')
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get list of all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    print("="*60)
    print(f"{'TILE INDEX - DATABASE STRUCTURE':^60}")
    print("="*60)

    for table in tables:
        table_name = table[0]
        if table_name == 'sqlite_sequence':
            continue
            
        print(f"\n[ TABLE: {table_name.upper()} ]")
        print("-" * 30)
        
        # Get column details
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        print(f"{'CID':<5} {'NAME':<20} {'TYPE':<10} {'NOTNULL':<8} {'PK':<5}")
        for col in columns:
            cid, name, dtype, notnull, dflt, pk = col
            print(f"{cid:<5} {name:<20} {dtype:<10} {notnull:<8} {pk:<5}")
            
        # Get index details (including UNIQUE)
        cursor.execute(f"PRAGMA index_list({table_name})")
        indexes = cursor.fetchall()
        if indexes:
            print("\n  Indexes/Constraints:")
            for idx in indexes:
                seq, name, unique, origin, partial = idx
                print(f"  - {name} (Unique: {unique})")
        
    conn.close()
    print("\n" + "="*60)

if __name__ == "__main__":
    print_db_structure()
