
import sqlite3
import os

def get_relationships():
    db_path = os.path.join(os.getcwd(), 'data', 'tile_index.db')
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    for table in tables:
        table_name = table[0]
        if table_name == 'sqlite_sequence':
            continue
            
        print(f"\n[ {table_name.upper()} ]")
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        fks = cursor.fetchall()
        if fks:
            for fk in fks:
                _, _, to_table, from_col, to_col, _, _, _ = fk
                print(f"  FK: {from_col} -> {to_table}({to_col})")
        else:
            # Check for column names that imply relationships if FKs aren't formal
            cursor.execute(f"PRAGMA table_info({table_name})")
            cols = cursor.fetchall()
            for col in cols:
                name = col[1]
                if name.endswith('_id'):
                    target = name.replace('_id', 's')
                    print(f"  Implicit FK: {name} -> {target}(id)")

    conn.close()

if __name__ == "__main__":
    get_relationships()
