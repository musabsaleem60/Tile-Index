"""
Stock Transaction model
Tracks Stock IN and Stock OUT operations
"""

from datetime import datetime


class StockTransaction:
    """Stock Transaction model class"""
    
    def __init__(self, id=None, user_id=None, branch_id=None, product_id=None,
                 grade=None, transaction_type=None, boxes=0, loose_pieces=0,
                 transaction_date=None, notes=None):
        self.id = id
        self.user_id = user_id
        self.branch_id = branch_id
        self.product_id = product_id
        self.grade = grade  # G1, G2, or G3
        self.transaction_type = transaction_type  # 'IN' or 'OUT'
        self.boxes = boxes
        self.loose_pieces = loose_pieces
        self.transaction_date = transaction_date if transaction_date else datetime.now()
        self.notes = notes
    
    def __repr__(self):
        return f"StockTransaction(id={self.id}, type='{self.transaction_type}', user_id={self.user_id}, product_id={self.product_id})"
    
    def to_dict(self):
        """Convert stock transaction to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'branch_id': self.branch_id,
            'product_id': self.product_id,
            'grade': self.grade,
            'transaction_type': self.transaction_type,
            'boxes': self.boxes,
            'loose_pieces': self.loose_pieces,
            'transaction_date': self.transaction_date,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create stock transaction from dictionary"""
        return cls(
            id=data.get('id'),
            user_id=data.get('user_id'),
            branch_id=data.get('branch_id'),
            product_id=data.get('product_id'),
            grade=data.get('grade'),
            transaction_type=data.get('transaction_type'),
            boxes=data.get('boxes', 0),
            loose_pieces=data.get('loose_pieces', 0),
            transaction_date=data.get('transaction_date'),
            notes=data.get('notes')
        )

