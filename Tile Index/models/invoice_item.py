"""
Invoice Item model
Represents a line item in an invoice
"""


class InvoiceItem:
    """Invoice Item model class"""
    
    def __init__(self, id=None, invoice_id=None, product_id=None, accessory_id=None,
                 sanitary_product_id=None, tile_size=None, grade=None, boxes=0, loose_pieces=0, rate_per_sqm=0,
                 rate_per_box=0, rate_per_piece=0, line_total=0, boxes_from_boxes=None, pieces_from_loose=None,
                 source_branch_id=None):
        self.id = id
        self.invoice_id = invoice_id
        self.product_id = product_id
        self.accessory_id = accessory_id
        self.sanitary_product_id = sanitary_product_id
        self.tile_size = tile_size
        self.grade = grade  # G1, G2, or G3
        self.boxes = boxes
        self.loose_pieces = loose_pieces
        self.rate_per_sqm = rate_per_sqm
        self.rate_per_box = rate_per_box
        self.rate_per_piece = rate_per_piece
        self.line_total = line_total
        self.boxes_from_boxes = boxes_from_boxes
        self.pieces_from_loose = pieces_from_loose
        self.source_branch_id = source_branch_id
    
    def __repr__(self):
        return f"InvoiceItem(id={self.id}, invoice_id={self.invoice_id}, product_id={self.product_id}, accessory_id={self.accessory_id}, sanitary_product_id={self.sanitary_product_id}, grade='{self.grade}', total={self.line_total})"
    
    def to_dict(self):
        """Convert invoice item to dictionary"""
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'product_id': self.product_id,
            'accessory_id': self.accessory_id,
            'sanitary_product_id': self.sanitary_product_id,
            'tile_size': self.tile_size,
            'grade': self.grade,
            'boxes': self.boxes,
            'loose_pieces': self.loose_pieces,
            'rate_per_sqm': self.rate_per_sqm,
            'rate_per_box': self.rate_per_box,
            'rate_per_piece': self.rate_per_piece,
            'line_total': self.line_total,
            'boxes_from_boxes': self.boxes_from_boxes,
            'pieces_from_loose': self.pieces_from_loose,
            'source_branch_id': self.source_branch_id
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create invoice item from dictionary"""
        return cls(
            id=data.get('id'),
            invoice_id=data.get('invoice_id'),
            product_id=data.get('product_id'),
            accessory_id=data.get('accessory_id'),
            sanitary_product_id=data.get('sanitary_product_id'),
            tile_size=data.get('tile_size'),
            grade=data.get('grade'),
            boxes=data.get('boxes', 0),
            loose_pieces=data.get('loose_pieces', 0),
            rate_per_sqm=data.get('rate_per_sqm', 0),
            rate_per_box=data.get('rate_per_box', 0),
            rate_per_piece=data.get('rate_per_piece', 0),
            line_total=data.get('line_total', 0),
            boxes_from_boxes=data.get('boxes_from_boxes'),
            pieces_from_loose=data.get('pieces_from_loose'),
            source_branch_id=data.get('source_branch_id')
        )

