"""
Database initialization module
Creates and initializes the SQLite database with all required tables
"""

import sqlite3
import os
from datetime import datetime


def get_db_path():
    """Get the database file path"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return os.path.join(data_dir, 'tile_index.db')


def init_database():
    """Initialize the database with all required tables"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Create branches table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS branches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            code TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            tile_size TEXT NOT NULL,
            area_per_box REAL NOT NULL,
            pieces_per_box INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(name, tile_size)
        )
    """)
    
    # Create inventory table (branch-wise, product-wise, grade-wise)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
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
    
    # Create invoices table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_id INTEGER NOT NULL,
            invoice_number TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            customer_contact TEXT,
            invoice_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            subtotal REAL NOT NULL DEFAULT 0,
            discount REAL NOT NULL DEFAULT 0,
            grand_total REAL NOT NULL DEFAULT 0,
            paid_amount REAL NOT NULL DEFAULT 0,
            balance REAL NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE CASCADE,
            UNIQUE(branch_id, invoice_number)
        )
    """)
    
    # Create invoice_items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoice_items (
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
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'employee')),
            branch_id INTEGER,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE SET NULL
        )
    """)
    
    # Create stock_transactions table (track Stock IN/OUT)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_transactions (
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
    
    # Create activity_log table (comprehensive audit log)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            user_role TEXT NOT NULL CHECK(user_role IN ('admin', 'employee')),
            branch_id INTEGER,
            branch_name TEXT,
            action_type TEXT NOT NULL,
            action_details TEXT,
            action_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
        )
    """)
    
    # Create accessories table (grouts, bonds, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accessories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL CHECK(category IN ('Grout', 'Bond', 'Floor Waste')),
            company TEXT NOT NULL,
            unit_price REAL NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(category, company)
        )
    """)
    
    # Create accessories_inventory table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accessories_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            branch_id INTEGER NOT NULL,
            accessory_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE CASCADE,
            FOREIGN KEY (accessory_id) REFERENCES accessories(id) ON DELETE CASCADE,
            UNIQUE(branch_id, accessory_id)
        )
    """)
    
    # Add accessory_id to invoice_items table (if column doesn't exist)
    try:
        cursor.execute("PRAGMA table_info(invoice_items)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'accessory_id' not in columns:
            cursor.execute("ALTER TABLE invoice_items ADD COLUMN accessory_id INTEGER")
            # We also need to relax constraints on existing columns if possible, 
            # but SQLite ALTER TABLE is limited. The recreate method is safer for full schema changes.
    except sqlite3.OperationalError:
        pass
    
    # Add user_id to invoices table (if column doesn't exist)
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(invoices)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'user_id' not in columns:
            cursor.execute("ALTER TABLE invoices ADD COLUMN user_id INTEGER")
            # Note: SQLite doesn't support adding foreign key constraints via ALTER TABLE
            # Foreign key will be enforced by application logic
    except sqlite3.OperationalError:
        # Column already exists, skip
        pass
    
    # Create indexes for better performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventory_branch_product_grade ON inventory(branch_id, product_id, grade)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_branch_number ON invoices(branch_id, invoice_number)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice ON invoice_items(invoice_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_transactions_user ON stock_transactions(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_transactions_date ON stock_transactions(transaction_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_invoices_user ON invoices(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_user ON activity_log(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_date ON activity_log(action_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_action ON activity_log(action_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_branch ON activity_log(branch_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_accessories_category ON accessories(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_accessories_inventory_branch ON accessories_inventory(branch_id, accessory_id)")
    
    # Insert default branches
    branches = [
        ('Tile Index – Korangi', 'TIK'),
        ('Tile Cera – Korangi', 'TCK'),
        ('Machi Mor', 'MM'),
        ('DHA', 'DHA')
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO branches (name, code) VALUES (?, ?)
    """, branches)
    
    # Insert default accessories (Grouts and Bonds)
    accessories = [
        # Grouts (name, category, company, unit_price)
        ('Grout', 'Grout', 'Shabir (White)', 400),
        ('Grout', 'Grout', 'Shabir (Almond)', 400),
        ('Grout', 'Grout', 'Shabir (Brown)', 400),
        ('Grout', 'Grout', 'Shabir (Marble Beige)', 400),
        ('Grout', 'Grout', 'Shabir (Sky Blue)', 400),
        ('Grout', 'Grout', 'Shabir (Inca Gold)', 400),
        ('Grout', 'Grout', 'Shabir (Smoke Grey)', 400),
        ('Grout', 'Grout', 'Shabir (Slate Grey)', 400),
        ('Grout', 'Grout', 'Shabir (Dark Grey)', 400),
        ('Grout', 'Grout', 'Shabir (Dark Brown)', 400),
        ('Grout', 'Grout', 'Shabir (Midnight Black)', 400),
        ('Grout', 'Grout', 'Strong (White)', 250),
        ('Grout', 'Grout', 'Strong (Ivory)', 250),
        ('Grout', 'Grout', 'Strong (Light Grey)', 250),
        ('Grout', 'Grout', 'Strong (Dark Grey)', 250),
        ('Grout', 'Grout', 'Strong (Light Brown)', 250),
        ('Grout', 'Grout', 'Strong (Dark Brown)', 250),
        ('Grout', 'Grout', 'Strong (Black)', 250),
        ('Grout', 'Grout', 'Strong (Sky Blue)', 250),
        ('Grout', 'Grout', 'Strong (Sage)', 250),
        # Bonds
        ('Bond', 'Bond', 'Shabir', 690),
        ('Bond', 'Bond', 'Stylo', 550),
        ('Bond', 'Bond', 'Sunny Star', 480),
        ('Bond', 'Bond', 'Elechem', 530),
        ('Bond', 'Bond', 'Ressichem', 580),
        # Floor Waste
        ('Floor Waste', 'Floor Waste', 'Heritage (Chrome)', 1700),
        ('Floor Waste', 'Floor Waste', 'Heritage (Black)', 2200),
        ('Floor Waste', 'Floor Waste', 'Heritage (White)', 1700),
    ]
    
    cursor.executemany("""
        INSERT OR IGNORE INTO accessories (name, category, company, unit_price) VALUES (?, ?, ?, ?)
    """, accessories)
    
    # Migrate existing grade data from old format to new format if needed
    # Import migration function
    try:
        from database.migrate_grades import migrate_grades_internal
        migrate_grades_internal(cursor, conn)
    except ImportError:
        # Migration module not available, skip
        pass
    except Exception as e:
        # Migration failed, but don't stop initialization
        print(f"Grade migration warning: {e}")
        pass
    
    # Create default admin user (password: musab123)
    # Using simple hash for demonstration (in production, use bcrypt or similar)
    import hashlib
    default_password = "musab123"
    password_hash = hashlib.sha256(default_password.encode()).hexdigest()
    
    cursor.execute("""
        INSERT OR IGNORE INTO users (username, password_hash, role, is_active)
        VALUES (?, ?, ?, ?)
    """, ('musab', password_hash, 'admin', 1))
    
    conn.commit()
    conn.close()
    return db_path


def get_connection():
    """Get a database connection"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

