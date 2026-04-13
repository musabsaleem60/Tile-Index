"""
Inventory Service
Business logic for inventory management
"""

from repositories.inventory_repository import InventoryRepository
from repositories.product_repository import ProductRepository
from repositories.stock_transaction_repository import StockTransactionRepository
from services.activity_log_service import ActivityLogService
from models.inventory import Inventory
from models.stock_transaction import StockTransaction
from datetime import datetime


class InventoryService:
    """Service for inventory operations"""
    
    @staticmethod
    def get_inventory(branch_id, product_id, grade):
        """Get inventory for a specific branch, product, and grade"""
        return InventoryRepository.get_by_branch_product_grade(branch_id, product_id, grade)
    
    @staticmethod
    def get_all_inventory(branch_id):
        """Get all inventory for a branch"""
        return InventoryRepository.get_all_by_branch(branch_id)
    
    @staticmethod
    def add_stock(branch_id, product_id, grade, boxes, loose_pieces, rate_per_sqm, rate_per_box, rate_per_piece, user_id=None):
        """Add stock to inventory (Stock IN)"""
        # Validate inputs
        if boxes < 0 or loose_pieces < 0:
            raise ValueError("Stock quantities cannot be negative")
        
        if rate_per_sqm < 0 or rate_per_box < 0 or rate_per_piece < 0:
            raise ValueError("Rates cannot be negative")
        
        # Get or create inventory record
        inventory = InventoryRepository.get_by_branch_product_grade(branch_id, product_id, grade)
        
        if inventory:
            # Update existing inventory
            inventory.boxes += boxes
            inventory.loose_pieces += loose_pieces
            inventory.rate_per_sqm = rate_per_sqm
            inventory.rate_per_box = rate_per_box
            inventory.rate_per_piece = rate_per_piece
        else:
            # Create new inventory
            inventory = Inventory(
                branch_id=branch_id,
                product_id=product_id,
                grade=grade,
                boxes=boxes,
                loose_pieces=loose_pieces,
                rate_per_sqm=rate_per_sqm,
                rate_per_box=rate_per_box,
                rate_per_piece=rate_per_piece
            )
        
        # Normalize pieces (convert to boxes if possible)
        product = ProductRepository.get_by_id(product_id)
        if product:
            while inventory.loose_pieces >= product.pieces_per_box:
                inventory.boxes += 1
                inventory.loose_pieces -= product.pieces_per_box
        
        inventory = InventoryRepository.create_or_update(inventory)
        
        # Record stock transaction
        if user_id:
            transaction = StockTransaction(
                user_id=user_id,
                branch_id=branch_id,
                product_id=product_id,
                grade=grade,
                transaction_type='IN',
                boxes=boxes,
                loose_pieces=loose_pieces,
                transaction_date=datetime.now(),
                notes=f"Stock IN - Rate: Rs.{rate_per_box}/box, Rs.{rate_per_piece}/piece"
            )
            StockTransactionRepository.create(transaction)
            
            # Log activity
            try:
                from repositories.user_repository import UserRepository
                user = UserRepository.get_by_id(user_id)
                if user:
                    product = ProductRepository.get_by_id(product_id)
                    product_name = product.name if product else f"Product {product_id}"
                    ActivityLogService.log_stock_in(user, branch_id, product_name, grade, boxes, loose_pieces)
            except:
                pass  # Don't fail if logging fails
        
        return inventory
    
    @staticmethod
    def deduct_stock(branch_id, product_id, grade, boxes, loose_pieces, user_id=None, notes=None):
        """Deduct stock from inventory (Stock OUT)"""
        # Validate inputs
        if boxes < 0 or loose_pieces < 0:
            raise ValueError("Deduction quantities cannot be negative")
        
        # Check available stock
        inventory = InventoryRepository.get_by_branch_product_grade(branch_id, product_id, grade)
        if not inventory:
            raise ValueError(f"No inventory found for this product and grade at this branch")
        
        # Get product to know pieces per box
        product = ProductRepository.get_by_id(product_id)
        if not product:
            raise ValueError(f"Product not found")
        
        # Calculate total pieces available
        total_available_pieces = (inventory.boxes * product.pieces_per_box) + inventory.loose_pieces
        
        # Calculate total pieces requested
        total_requested_pieces = (boxes * product.pieces_per_box) + loose_pieces
        
        # Check if sufficient stock
        if total_requested_pieces > total_available_pieces:
            raise ValueError(f"Insufficient stock. Available: {inventory.boxes} boxes + {inventory.loose_pieces} pieces. Requested: {boxes} boxes + {loose_pieces} pieces")
        
        # Deduct stock
        inventory = InventoryRepository.update_stock(branch_id, product_id, grade, -boxes, -loose_pieces)
        
        # Record stock transaction
        if user_id:
            transaction = StockTransaction(
                user_id=user_id,
                branch_id=branch_id,
                product_id=product_id,
                grade=grade,
                transaction_type='OUT',
                boxes=boxes,
                loose_pieces=loose_pieces,
                transaction_date=datetime.now(),
                notes=notes or "Stock OUT"
            )
            StockTransactionRepository.create(transaction)
            
            # Log activity
            try:
                from repositories.user_repository import UserRepository
                user = UserRepository.get_by_id(user_id)
                if user:
                    product = ProductRepository.get_by_id(product_id)
                    product_name = product.name if product else f"Product {product_id}"
                    ActivityLogService.log_stock_out(user, branch_id, product_name, grade, boxes, loose_pieces, notes)
            except:
                pass  # Don't fail if logging fails
        
        return inventory
    
    @staticmethod
    def check_low_stock(branch_id, product_id, grade, threshold_boxes=5):
        """Check if stock is low (below threshold)"""
        inventory = InventoryRepository.get_by_branch_product_grade(branch_id, product_id, grade)
        if not inventory:
            return True, 0, 0  # No stock = low stock
        
        total_boxes = inventory.boxes
        if inventory.loose_pieces > 0:
            total_boxes += 0.5  # Consider partial box
        
        is_low = total_boxes < threshold_boxes
        return is_low, inventory.boxes, inventory.loose_pieces

