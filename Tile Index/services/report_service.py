"""
Report Service
Business logic for generating reports
"""

from database.init_db import get_connection
from datetime import datetime, timedelta
from repositories.branch_repository import BranchRepository
from repositories.product_repository import ProductRepository
from repositories.inventory_repository import InventoryRepository


class ReportService:
    """Service for report generation"""
    
    @staticmethod
    def get_daily_sales_report(branch_id, date=None):
        """Get daily sales report for a branch"""
        if not date:
            date = datetime.now().date()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get all invoices for the date
        cursor.execute("""
            SELECT i.id, i.invoice_number, i.customer_name, i.invoice_date,
                   i.subtotal, i.discount, i.grand_total, i.paid_amount, i.balance
            FROM invoices i
            WHERE i.branch_id = ? AND DATE(i.invoice_date) = ?
            ORDER BY i.invoice_date
        """, (branch_id, date))
        
        invoices = cursor.fetchall()
        
        # Calculate totals
        total_invoices = len(invoices)
        total_sales = sum(row[6] for row in invoices)  # grand_total
        total_paid = sum(row[7] for row in invoices)  # paid_amount
        total_balance = sum(row[8] for row in invoices)  # balance
        
        conn.close()
        
        return {
            'date': date,
            'branch_id': branch_id,
            'total_invoices': total_invoices,
            'total_sales': total_sales,
            'total_paid': total_paid,
            'total_balance': total_balance,
            'invoices': [
                {
                    'invoice_number': inv[1],
                    'customer_name': inv[2],
                    'invoice_date': inv[3],
                    'grand_total': inv[6],
                    'paid_amount': inv[7],
                    'balance': inv[8]
                }
                for inv in invoices
            ]
        }
    
    @staticmethod
    def get_branch_stock_report(branch_id):
        """Get complete stock report for a branch"""
        inventory_list = InventoryRepository.get_all_by_branch(branch_id)
        products = {p.id: p for p in ProductRepository.get_all()}
        
        report_data = []
        total_value = 0
        
        for inv in inventory_list:
            product = products.get(inv.product_id)
            if not product:
                continue
            
            total_pieces = (inv.boxes * product.pieces_per_box) + inv.loose_pieces
            total_area = (inv.boxes * product.area_per_box) + (inv.loose_pieces * product.area_per_box / product.pieces_per_box)
            
            # Calculate stock value (using rate per box and rate per piece)
            stock_value = (inv.boxes * inv.rate_per_box) + (inv.loose_pieces * inv.rate_per_piece)
            total_value += stock_value
            
            report_data.append({
                'product_id': product.id,
                'product_name': product.name,
                'tile_size': product.tile_size,
                'grade': inv.grade,
                'boxes': inv.boxes,
                'loose_pieces': inv.loose_pieces,
                'total_pieces': total_pieces,
                'total_area': total_area,
                'rate_per_box': inv.rate_per_box,
                'rate_per_piece': inv.rate_per_piece,
                'stock_value': stock_value
            })
        
        # Get branch name
        branch = BranchRepository.get_by_id(branch_id)
        branch_name = branch.name if branch else f"Branch {branch_id}"
        
        return {
            'branch_id': branch_id,
            'branch_name': branch_name,
            'total_value': total_value,
            'items': report_data
        }
    
    @staticmethod
    def get_complete_business_stock_report():
        """Get complete business stock report for all branches"""
        from repositories.branch_repository import BranchRepository
        
        branches = BranchRepository.get_all()
        products = {p.id: p for p in ProductRepository.get_all()}
        
        report_data = {
            'total_branches': len(branches),
            'total_products': len(products),
            'total_value': 0,
            'branches': []
        }
        
        for branch in branches:
            branch_inventory = InventoryRepository.get_all_by_branch(branch.id)
            
            branch_items = []
            branch_total_value = 0
            
            for inv in branch_inventory:
                product = products.get(inv.product_id)
                if not product:
                    continue
                
                total_pieces = (inv.boxes * product.pieces_per_box) + inv.loose_pieces
                total_area = (inv.boxes * product.area_per_box) + (inv.loose_pieces * product.area_per_box / product.pieces_per_box)
                
                # Calculate stock value
                stock_value = (inv.boxes * inv.rate_per_box) + (inv.loose_pieces * inv.rate_per_piece)
                branch_total_value += stock_value
                
                branch_items.append({
                    'product_id': product.id,
                    'product_name': product.name,
                    'tile_size': product.tile_size,
                    'grade': inv.grade,
                    'boxes': inv.boxes,
                    'loose_pieces': inv.loose_pieces,
                    'total_pieces': total_pieces,
                    'total_area': total_area,
                    'rate_per_box': inv.rate_per_box,
                    'rate_per_piece': inv.rate_per_piece,
                    'stock_value': stock_value
                })
            
            report_data['branches'].append({
                'branch_id': branch.id,
                'branch_name': branch.name,
                'items': branch_items,
                'branch_total_value': branch_total_value
            })
            
            report_data['total_value'] += branch_total_value
        
        return report_data

