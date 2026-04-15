"""
Accessory Service
Business logic for accessory inventory management (grouts, bonds)
"""

from repositories.accessory_repository import AccessoryRepository, AccessoryInventoryRepository
from models.accessory import Accessory


class AccessoryService:
    """Service for accessory operations"""
    
    @staticmethod
    def get_all_accessories():
        """Get all accessories"""
        return AccessoryRepository.get_all()
    
    @staticmethod
    def get_accessories_by_category(category):
        """Get accessories by category"""
        return AccessoryRepository.get_by_category(category)
    
    @staticmethod
    def get_grouts():
        """Get all grout accessories"""
        return AccessoryRepository.get_by_category(Accessory.CATEGORY_GROUT)
    
    @staticmethod
    def get_bonds():
        """Get all bond accessories"""
        return AccessoryRepository.get_by_category(Accessory.CATEGORY_BOND)
    
    @staticmethod
    def add_accessory(name, category, company, unit_price):
        """Add a new accessory"""
        if category not in Accessory.VALID_CATEGORIES:
            raise ValueError(f"Invalid category. Must be one of: {Accessory.VALID_CATEGORIES}")
        if unit_price < 0:
            raise ValueError("Unit price cannot be negative")
        
        accessory = Accessory(
            name=name,
            category=category,
            company=company,
            unit_price=unit_price
        )
        return AccessoryRepository.create(accessory)
    
    @staticmethod
    def update_accessory(accessory_id, name, category, company, unit_price):
        """Update an accessory"""
        accessory = AccessoryRepository.get_by_id(accessory_id)
        if not accessory:
            raise ValueError("Accessory not found")
        
        if category not in Accessory.VALID_CATEGORIES:
            raise ValueError(f"Invalid category. Must be one of: {Accessory.VALID_CATEGORIES}")
        
        accessory.name = name
        accessory.category = category
        accessory.company = company
        accessory.unit_price = unit_price
        return AccessoryRepository.update(accessory)
    
    @staticmethod
    def delete_accessory(accessory_id):
        """Delete an accessory"""
        AccessoryRepository.delete(accessory_id)
    
    @staticmethod
    def get_inventory(branch_id, accessory_id):
        """Get inventory for a specific accessory at a branch"""
        return AccessoryInventoryRepository.get_by_branch_accessory(branch_id, accessory_id)
    
    @staticmethod
    def get_all_inventory(branch_id):
        """Get all accessory inventory for a branch"""
        return AccessoryInventoryRepository.get_all_by_branch(branch_id)
    
    @staticmethod
    def add_stock(branch_id, accessory_id, quantity):
        """Add stock for an accessory at a branch"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        return AccessoryInventoryRepository.add_stock(branch_id, accessory_id, quantity)
    
    @staticmethod
    def deduct_stock(branch_id, accessory_id, quantity):
        """Deduct stock for an accessory at a branch"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        return AccessoryInventoryRepository.deduct_stock(branch_id, accessory_id, quantity)
    
    @staticmethod
    def set_stock(branch_id, accessory_id, quantity):
        """Set stock to a specific quantity"""
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")
        return AccessoryInventoryRepository.create_or_update(branch_id, accessory_id, quantity)
