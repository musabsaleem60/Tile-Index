"""
Invoice Repository
Data access layer for invoices
"""

import sqlite3
from database.init_db import get_connection
from models.invoice import Invoice
from models.invoice_item import InvoiceItem


class InvoiceRepository:
    """Repository for invoice operations"""
    
    @staticmethod
    def get_next_invoice_number(branch_id):
        """Get next invoice number for a branch"""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get branch code
        cursor.execute("SELECT code FROM branches WHERE id = ?", (branch_id,))
        branch_row = cursor.fetchone()
        if not branch_row:
            conn.close()
            raise ValueError(f"Branch with id {branch_id} not found")
        
        branch_code = branch_row[0]
        
        # Get last invoice number for this branch
        cursor.execute("""
            SELECT invoice_number FROM invoices
            WHERE branch_id = ?
            ORDER BY id DESC LIMIT 1
        """, (branch_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # Extract number from format like "TIK-001" or "TIK-0001"
            last_number = row[0]
            try:
                # Split by dash and get the number part
                parts = last_number.split('-')
                if len(parts) == 2:
                    num = int(parts[1])
                    next_num = num + 1
                else:
                    next_num = 1
            except:
                next_num = 1
        else:
            next_num = 1
        
        # Format as 4-digit number with leading zeros
        return f"{branch_code}-{next_num:04d}"
    
    @staticmethod
    def create(invoice):
        """Create a new invoice with items"""
        conn = get_connection()
        cursor = conn.cursor()
        
        try:
            # Generate invoice number if not provided
            if not invoice.invoice_number:
                invoice.invoice_number = InvoiceRepository.get_next_invoice_number(invoice.branch_id)
            
            # Insert invoice (check if user_id column exists)
            try:
                cursor.execute("""
                    INSERT INTO invoices (branch_id, invoice_number, customer_name, customer_contact,
                                        invoice_date, subtotal, discount, grand_total, paid_amount, balance, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (invoice.branch_id, invoice.invoice_number, invoice.customer_name,
                      invoice.customer_contact, invoice.invoice_date, invoice.subtotal,
                      invoice.discount, invoice.grand_total, invoice.paid_amount, invoice.balance,
                      getattr(invoice, 'user_id', None)))
            except sqlite3.OperationalError:
                # user_id column doesn't exist yet, insert without it
                cursor.execute("""
                    INSERT INTO invoices (branch_id, invoice_number, customer_name, customer_contact,
                                        invoice_date, subtotal, discount, grand_total, paid_amount, balance)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (invoice.branch_id, invoice.invoice_number, invoice.customer_name,
                      invoice.customer_contact, invoice.invoice_date, invoice.subtotal,
                      invoice.discount, invoice.grand_total, invoice.paid_amount, invoice.balance))
            
            invoice.id = cursor.lastrowid
            
            # Insert invoice items
            for item in invoice.items:
                cursor.execute("""
                    INSERT INTO invoice_items (invoice_id, product_id, tile_size, grade,
                                             boxes, loose_pieces, rate_per_sqm, rate_per_box,
                                             rate_per_piece, line_total)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (invoice.id, item.product_id, item.tile_size, item.grade,
                      item.boxes, item.loose_pieces, item.rate_per_sqm, item.rate_per_box,
                      item.rate_per_piece, item.line_total))
                item.id = cursor.lastrowid
                item.invoice_id = invoice.id
            
            conn.commit()
            conn.close()
            return invoice
            
        except Exception as e:
            conn.rollback()
            conn.close()
            raise e
    
    @staticmethod
    def get_by_id(invoice_id):
        """Get invoice by ID with items"""
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get invoice (check if user_id column exists)
        try:
            cursor.execute("PRAGMA table_info(invoices)")
            columns = [col[1] for col in cursor.fetchall()]
            has_user_id = 'user_id' in columns
            
            if has_user_id:
                cursor.execute("""
                    SELECT id, branch_id, invoice_number, customer_name, customer_contact,
                           invoice_date, subtotal, discount, grand_total, paid_amount, balance, created_at, user_id
                    FROM invoices WHERE id = ?
                """, (invoice_id,))
            else:
                cursor.execute("""
                    SELECT id, branch_id, invoice_number, customer_name, customer_contact,
                           invoice_date, subtotal, discount, grand_total, paid_amount, balance, created_at
                    FROM invoices WHERE id = ?
                """, (invoice_id,))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return None
            
            if has_user_id and len(row) >= 13:
                invoice = Invoice(id=row[0], branch_id=row[1], invoice_number=row[2],
                                 customer_name=row[3], customer_contact=row[4], invoice_date=row[5],
                                 subtotal=row[6], discount=row[7], grand_total=row[8],
                                 paid_amount=row[9], balance=row[10], created_at=row[11], user_id=row[12])
            else:
                invoice = Invoice(id=row[0], branch_id=row[1], invoice_number=row[2],
                                 customer_name=row[3], customer_contact=row[4], invoice_date=row[5],
                                 subtotal=row[6], discount=row[7], grand_total=row[8],
                                 paid_amount=row[9], balance=row[10], created_at=row[11], user_id=None)
            
            # Get invoice items
            cursor.execute("""
                SELECT id, invoice_id, product_id, tile_size, grade, boxes, loose_pieces,
                       rate_per_sqm, rate_per_box, rate_per_piece, line_total
                FROM invoice_items WHERE invoice_id = ?
                ORDER BY id
            """, (invoice_id,))
            item_rows = cursor.fetchall()
            
            invoice.items = [InvoiceItem(id=r[0], invoice_id=r[1], product_id=r[2],
                                        tile_size=r[3], grade=r[4], boxes=r[5],
                                        loose_pieces=r[6], rate_per_sqm=r[7],
                                        rate_per_box=r[8], rate_per_piece=r[9],
                                        line_total=r[10]) for r in item_rows]
            
            conn.close()
            return invoice
            
        except Exception as e:
            conn.close()
            raise e
        
        # Get invoice items
        cursor.execute("""
            SELECT id, invoice_id, product_id, tile_size, grade, boxes, loose_pieces,
                   rate_per_sqm, rate_per_box, rate_per_piece, line_total
            FROM invoice_items WHERE invoice_id = ?
            ORDER BY id
        """, (invoice_id,))
        item_rows = cursor.fetchall()
        
        invoice.items = [InvoiceItem(id=r[0], invoice_id=r[1], product_id=r[2],
                                    tile_size=r[3], grade=r[4], boxes=r[5],
                                    loose_pieces=r[6], rate_per_sqm=r[7],
                                    rate_per_box=r[8], rate_per_piece=r[9],
                                    line_total=r[10]) for r in item_rows]
        
        conn.close()
        return invoice
    
    @staticmethod
    def search(branch_id=None, invoice_number=None, customer_name=None, date_from=None, date_to=None):
        """Search invoices with filters"""
        conn = get_connection()
        cursor = conn.cursor()
        
        query = "SELECT id, branch_id, invoice_number, customer_name, customer_contact, invoice_date, subtotal, discount, grand_total, paid_amount, balance, created_at FROM invoices WHERE 1=1"
        params = []
        
        if branch_id:
            query += " AND branch_id = ?"
            params.append(branch_id)
        
        if invoice_number:
            query += " AND invoice_number LIKE ?"
            params.append(f"%{invoice_number}%")
        
        if customer_name:
            query += " AND customer_name LIKE ?"
            params.append(f"%{customer_name}%")
        
        if date_from:
            query += " AND DATE(invoice_date) >= ?"
            params.append(date_from)
        
        if date_to:
            query += " AND DATE(invoice_date) <= ?"
            params.append(date_to)
        
        query += " ORDER BY invoice_date DESC, id DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [Invoice(id=r[0], branch_id=r[1], invoice_number=r[2], customer_name=r[3],
                       customer_contact=r[4], invoice_date=r[5], subtotal=r[6],
                       discount=r[7], grand_total=r[8], paid_amount=r[9],
                       balance=r[10], created_at=r[11]) for r in rows]

