"""
Inventory model
Represents inventory stock for a product at a branch with specific grade
"""


class Inventory:
    """Inventory model class"""
    
    def __init__(self, id=None, branch_id=None, product_id=None, grade=None,
                 boxes=0, loose_pieces=0, rate_per_sqm=0, rate_per_box=0,
                 rate_per_piece=0, updated_at=None):
        self.id = id
        self.branch_id = branch_id
        self.product_id = product_id
        self.grade = grade  # G1, G2, or G3
        self.boxes = boxes
        self.loose_pieces = loose_pieces
        self.rate_per_sqm = rate_per_sqm
        self.rate_per_box = rate_per_box
        self.rate_per_piece = rate_per_piece
        self.updated_at = updated_at
    
    def get_total_pieces(self, pieces_per_box):
        """Calculate total pieces (boxes converted to pieces + loose pieces)"""
        return (self.boxes * pieces_per_box) + self.loose_pieces
    
    def __repr__(self):
        return f"Inventory(id={self.id}, branch_id={self.branch_id}, product_id={self.product_id}, grade='{self.grade}', boxes={self.boxes}, pieces={self.loose_pieces})"
    
    def to_dict(self):
        """Convert inventory to dictionary"""
        return {
            'id': self.id,
            'branch_id': self.branch_id,
            'product_id': self.product_id,
            'grade': self.grade,
            'boxes': self.boxes,
            'loose_pieces': self.loose_pieces,
            'rate_per_sqm': self.rate_per_sqm,
            'rate_per_box': self.rate_per_box,
            'rate_per_piece': self.rate_per_piece,
            'updated_at': self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create inventory from dictionary"""
        return cls(
            id=data.get('id'),
            branch_id=data.get('branch_id'),
            product_id=data.get('product_id'),
            grade=data.get('grade'),
            boxes=data.get('boxes', 0),
            loose_pieces=data.get('loose_pieces', 0),
            rate_per_sqm=data.get('rate_per_sqm', 0),
            rate_per_box=data.get('rate_per_box', 0),
            rate_per_piece=data.get('rate_per_piece', 0),
            updated_at=data.get('updated_at')
        )

