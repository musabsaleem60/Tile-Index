"""
Product model
Represents a tile product
"""


class Product:
    """Product model class"""
    
    def __init__(self, id=None, name=None, tile_size=None, area_per_box=None, 
                 pieces_per_box=None, created_at=None):
        self.id = id
        self.name = name
        self.tile_size = tile_size
        self.area_per_box = area_per_box
        self.pieces_per_box = pieces_per_box
        self.created_at = created_at
    
    def __repr__(self):
        return f"Product(id={self.id}, name='{self.name}', size='{self.tile_size}')"
    
    def to_dict(self):
        """Convert product to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'tile_size': self.tile_size,
            'area_per_box': self.area_per_box,
            'pieces_per_box': self.pieces_per_box,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create product from dictionary"""
        return cls(
            id=data.get('id'),
            name=data.get('name'),
            tile_size=data.get('tile_size'),
            area_per_box=data.get('area_per_box'),
            pieces_per_box=data.get('pieces_per_box'),
            created_at=data.get('created_at')
        )

