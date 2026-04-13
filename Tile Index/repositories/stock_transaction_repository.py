"""
Stock Transaction Repository
Data access layer for stock transactions
"""

from database.init_db import get_connection
from models.stock_transaction import StockTransaction


class StockTransactionRepository:
    """Repository for stock transaction operations"""
    
    @staticmethod
    def create(transaction):
        """Create a new stock transaction"""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO stock_transactions (user_id, branch_id, product_id, grade,
                                          transaction_type, boxes, loose_pieces, transaction_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (transaction.user_id, transaction.branch_id, transaction.product_id,
              transaction.grade, transaction.transaction_type, transaction.boxes,
              transaction.loose_pieces, transaction.transaction_date, transaction.notes))
        
        transaction.id = cursor.lastrowid
        conn.commit()
        conn.close()
        return transaction
    
    @staticmethod
    def get_by_user(user_id, limit=100):
        """Get stock transactions by user"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, branch_id, product_id, grade, transaction_type,
                   boxes, loose_pieces, transaction_date, notes
            FROM stock_transactions
            WHERE user_id = ?
            ORDER BY transaction_date DESC
            LIMIT ?
        """, (user_id, limit))
        rows = cursor.fetchall()
        conn.close()
        
        return [StockTransaction(id=r[0], user_id=r[1], branch_id=r[2], product_id=r[3],
                                grade=r[4], transaction_type=r[5], boxes=r[6],
                                loose_pieces=r[7], transaction_date=r[8], notes=r[9]) for r in rows]
    
    @staticmethod
    def get_by_branch(branch_id, limit=100):
        """Get stock transactions by branch"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, branch_id, product_id, grade, transaction_type,
                   boxes, loose_pieces, transaction_date, notes
            FROM stock_transactions
            WHERE branch_id = ?
            ORDER BY transaction_date DESC
            LIMIT ?
        """, (branch_id, limit))
        rows = cursor.fetchall()
        conn.close()
        
        return [StockTransaction(id=r[0], user_id=r[1], branch_id=r[2], product_id=r[3],
                                grade=r[4], transaction_type=r[5], boxes=r[6],
                                loose_pieces=r[7], transaction_date=r[8], notes=r[9]) for r in rows]
    
    @staticmethod
    def get_all(limit=100):
        """Get all stock transactions"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, branch_id, product_id, grade, transaction_type,
                   boxes, loose_pieces, transaction_date, notes
            FROM stock_transactions
            ORDER BY transaction_date DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        return [StockTransaction(id=r[0], user_id=r[1], branch_id=r[2], product_id=r[3],
                                grade=r[4], transaction_type=r[5], boxes=r[6],
                                loose_pieces=r[7], transaction_date=r[8], notes=r[9]) for r in rows]

