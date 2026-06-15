"""
Sanitary Service
Business logic for sanitary product and inventory management
"""

from models.sanitary import SanitaryProduct
from repositories.sanitary_repository import (
    SanitaryProductRepository,
    SanitaryInventoryRepository,
    SanitaryStockTransactionRepository,
)


class SanitaryService:
    """Service for sanitary product operations"""

    @staticmethod
    def get_all_products(company=None, product_category=None, color=None):
        """Get all sanitary products"""
        return SanitaryProductRepository.get_all(company, product_category, color)

    @staticmethod
    def get_product(sanitary_product_id):
        """Get sanitary product by ID"""
        return SanitaryProductRepository.get_by_id(sanitary_product_id)

    @staticmethod
    def add_product(company_name, product_category, color, purchase_price, sale_price, sku):
        """Add a new sanitary product"""
        SanitaryService._validate_product(company_name, product_category, color, purchase_price, sale_price, sku)

        product = SanitaryProduct(
            company_name=company_name,
            product_category=product_category,
            color=color,
            purchase_price=purchase_price,
            sale_price=sale_price,
            sku=sku
        )
        return SanitaryProductRepository.create(product)

    @staticmethod
    def update_product(sanitary_product_id, company_name, product_category, color,
                       purchase_price, sale_price, sku):
        """Update a sanitary product"""
        product = SanitaryProductRepository.get_by_id(sanitary_product_id)
        if not product:
            raise ValueError("Sanitary product not found")

        SanitaryService._validate_product(company_name, product_category, color, purchase_price, sale_price, sku)

        product.company_name = company_name
        product.product_category = product_category
        product.color = color
        product.purchase_price = purchase_price
        product.sale_price = sale_price
        product.sku = sku
        return SanitaryProductRepository.update(product)

    @staticmethod
    def delete_product(sanitary_product_id):
        """Delete a sanitary product"""
        SanitaryProductRepository.delete(sanitary_product_id)

    @staticmethod
    def get_inventory(branch_id, sanitary_product_id):
        """Get inventory for a sanitary product at a branch"""
        return SanitaryInventoryRepository.get_by_branch_product(branch_id, sanitary_product_id)

    @staticmethod
    def get_all_inventory(branch_id, company=None, product_category=None, color=None):
        """Get all sanitary inventory for a branch"""
        return SanitaryInventoryRepository.get_all_by_branch(branch_id, company, product_category, color)

    @staticmethod
    def add_stock(branch_id, sanitary_product_id, quantity, user_id=None, notes=None):
        """Add stock for a sanitary product at a branch"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        result = SanitaryInventoryRepository.add_stock(branch_id, sanitary_product_id, quantity)
        if user_id:
            SanitaryStockTransactionRepository.create(
                user_id, branch_id, sanitary_product_id, 'IN', quantity, notes or "Sanitary Stock IN"
            )
        return result

    @staticmethod
    def deduct_stock(branch_id, sanitary_product_id, quantity, user_id=None, notes=None):
        """Deduct stock for a sanitary product at a branch"""
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        result = SanitaryInventoryRepository.deduct_stock(branch_id, sanitary_product_id, quantity)
        if user_id:
            SanitaryStockTransactionRepository.create(
                user_id, branch_id, sanitary_product_id, 'OUT', quantity, notes or "Sanitary Stock OUT"
            )
        return result

    @staticmethod
    def set_stock(branch_id, sanitary_product_id, quantity):
        """Set stock to a specific quantity"""
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")
        return SanitaryInventoryRepository.create_or_update(branch_id, sanitary_product_id, quantity)

    @staticmethod
    def _validate_product(company_name, product_category, color, purchase_price, sale_price, sku):
        """Validate sanitary product fields"""
        if not company_name or not company_name.strip():
            raise ValueError("Company name is required")
        if not product_category or not product_category.strip():
            raise ValueError("Product category is required")
        if not color or not color.strip():
            raise ValueError("Color is required")
        if not sku or not sku.strip():
            raise ValueError("SKU/Article code is required")
        if purchase_price < 0:
            raise ValueError("Purchase price cannot be negative")
        if sale_price < 0:
            raise ValueError("Sale price cannot be negative")
