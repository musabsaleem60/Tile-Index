"""
Report Service
Business logic for generating reports
"""

from database.init_db import get_connection
from datetime import datetime, timedelta
from repositories.branch_repository import BranchRepository
from repositories.product_repository import ProductRepository
from repositories.inventory_repository import InventoryRepository
from repositories.sanitary_repository import SanitaryInventoryRepository
from repositories.sanitary_repository import SanitaryProductRepository
from services.invoice_service import InvoiceService
from desktop_client.remote_state import is_api_authenticated
from desktop_client.session import api_client
from desktop_client.api_client import ApiClientError


class ReportService:
    """Service for report generation"""
    
    @staticmethod
    def get_daily_sales_report(branch_id, date=None):
        """Get daily sales report for a branch"""
        if is_api_authenticated():
            if not date:
                date = datetime.now().date()
            date_str = str(date)
            data = api_client.get(f"/reports/daily-sales/{branch_id}?report_date={date_str}")
            if "invoices" not in data:
                invoices = [
                    inv for inv in InvoiceService.search_invoices(branch_id=branch_id, date_from=date_str, date_to=date_str)
                    if getattr(inv, 'status', 'active') == 'active'
                ]
                data = dict(data)
                data["invoices"] = [
                    {
                        "invoice_number": inv.invoice_number,
                        "customer_name": inv.customer_name,
                        "invoice_date": inv.invoice_date,
                        "grand_total": inv.grand_total,
                        "paid_amount": inv.paid_amount,
                        "balance": inv.balance,
                    }
                    for inv in invoices
                ]
            return data

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
              AND COALESCE(i.status, 'active') = 'active'
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
        if is_api_authenticated():
            data = api_client.get(f"/reports/stock/{branch_id}")
            if "items" in data or "sanitary_items" in data:
                return data

        inventory_list = InventoryRepository.get_all_by_branch(branch_id)
        products = {p.id: p for p in ProductRepository.get_all()}
        sanitary_products = {p.id: p for p in SanitaryProductRepository.get_all()} if is_api_authenticated() else {}
        
        report_data = []
        sanitary_report_data = []
        total_value = 0
        
        for inv in inventory_list:
            product = products.get(inv.product_id)
            if not product:
                continue
            
            total_pieces = (inv.boxes * product.pieces_per_box) + inv.loose_pieces
            total_area = (inv.boxes * product.area_per_box) + (inv.loose_pieces * product.area_per_box / product.pieces_per_box)
            
            price = ReportService._resolve_local_tile_price(product, inv.grade)
            stock_value = None
            if price:
                stock_value = (inv.boxes * price["rate_per_box"]) + (inv.loose_pieces * price["rate_per_piece"])
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
                'rate_per_box': price["rate_per_box"] if price else None,
                'rate_per_piece': price["rate_per_piece"] if price else None,
                'stock_value': stock_value,
                'value_display': f"Rs. {stock_value:.2f}" if price else "No Rate Set"
            })

        sanitary_inventory = SanitaryInventoryRepository.get_all_by_branch(branch_id)
        for inv in sanitary_inventory:
            product = sanitary_products.get(inv.sanitary_product_id)
            sale_price = getattr(inv, 'sale_price', None)
            if sale_price is None and product:
                sale_price = product.sale_price
                inv.company_name = product.company_name
                inv.product_category = product.product_category
                inv.color = product.color
                inv.sku = product.sku
                inv.purchase_price = product.purchase_price
            sale_price = sale_price or 0
            stock_value = inv.quantity * sale_price
            total_value += stock_value

            sanitary_report_data.append({
                'sanitary_product_id': inv.sanitary_product_id,
                'company_name': inv.company_name,
                'product_category': inv.product_category,
                'color': inv.color,
                'sku': inv.sku,
                'quantity': inv.quantity,
                'purchase_price': inv.purchase_price,
                'sale_price': sale_price,
                'stock_value': stock_value
            })
        
        # Get branch name
        branch = BranchRepository.get_by_id(branch_id)
        branch_name = branch.name if branch else f"Branch {branch_id}"
        
        return {
            'branch_id': branch_id,
            'branch_name': branch_name,
            'total_value': total_value,
            'items': report_data,
            'sanitary_items': sanitary_report_data
        }
    
    @staticmethod
    def get_complete_business_stock_report():
        """Get complete business stock report for all branches"""
        if is_api_authenticated():
            data = api_client.get("/reports/business-stock")
            if "branches" in data:
                return data

        from repositories.branch_repository import BranchRepository
        
        branches = BranchRepository.get_all()
        products = {p.id: p for p in ProductRepository.get_all()}
        sanitary_products = {p.id: p for p in SanitaryProductRepository.get_all()} if is_api_authenticated() else {}
        
        report_data = {
            'total_branches': len(branches),
            'total_products': len(products),
            'total_sanitary_products': 0,
            'total_value': 0,
            'branches': []
        }
        
        for branch in branches:
            branch_inventory = InventoryRepository.get_all_by_branch(branch.id)
            sanitary_inventory = SanitaryInventoryRepository.get_all_by_branch(branch.id)
            
            branch_items = []
            sanitary_items = []
            branch_total_value = 0
            
            for inv in branch_inventory:
                product = products.get(inv.product_id)
                if not product:
                    continue
                
                total_pieces = (inv.boxes * product.pieces_per_box) + inv.loose_pieces
                total_area = (inv.boxes * product.area_per_box) + (inv.loose_pieces * product.area_per_box / product.pieces_per_box)
                
                price = ReportService._resolve_local_tile_price(product, inv.grade)
                stock_value = None
                if price:
                    stock_value = (inv.boxes * price["rate_per_box"]) + (inv.loose_pieces * price["rate_per_piece"])
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
                    'rate_per_box': price["rate_per_box"] if price else None,
                    'rate_per_piece': price["rate_per_piece"] if price else None,
                    'stock_value': stock_value,
                    'value_display': f"Rs. {stock_value:.2f}" if price else "No Rate Set"
                })

            for inv in sanitary_inventory:
                product = sanitary_products.get(inv.sanitary_product_id)
                sale_price = getattr(inv, 'sale_price', None)
                if sale_price is None and product:
                    sale_price = product.sale_price
                    inv.company_name = product.company_name
                    inv.product_category = product.product_category
                    inv.color = product.color
                    inv.sku = product.sku
                    inv.purchase_price = product.purchase_price
                sale_price = sale_price or 0
                stock_value = inv.quantity * sale_price
                branch_total_value += stock_value
                sanitary_items.append({
                    'sanitary_product_id': inv.sanitary_product_id,
                    'company_name': inv.company_name,
                    'product_category': inv.product_category,
                    'color': inv.color,
                    'sku': inv.sku,
                    'quantity': inv.quantity,
                    'purchase_price': inv.purchase_price,
                    'sale_price': sale_price,
                    'stock_value': stock_value
                })
            
            report_data['branches'].append({
                'branch_id': branch.id,
                'branch_name': branch.name,
                'items': branch_items,
                'sanitary_items': sanitary_items,
                'branch_total_value': branch_total_value
            })
            
            report_data['total_value'] += branch_total_value
            report_data['total_sanitary_products'] += len(sanitary_items)
        
        return report_data

    @staticmethod
    def get_monthly_sales_report(date_from, date_to, branch_id=None):
        """Get monthly sales totals grouped by month and branch."""
        if is_api_authenticated():
            path = f"/reports/monthly-sales?date_from={date_from}&date_to={date_to}"
            if branch_id:
                path += f"&branch_id={branch_id}"
            try:
                return api_client.get(path)
            except ApiClientError:
                pass

        invoices = [
            inv for inv in InvoiceService.search_invoices(branch_id=branch_id, date_from=str(date_from), date_to=str(date_to))
            if getattr(inv, 'status', 'active') == 'active'
        ]
        branches = {branch.id: branch for branch in BranchRepository.get_all()}
        buckets = {}
        for inv in invoices:
            month = str(inv.invoice_date)[:7]
            key = (month, inv.branch_id)
            bucket = buckets.setdefault(key, {
                "month": month,
                "branch_id": inv.branch_id,
                "branch_name": branches.get(inv.branch_id).name if branches.get(inv.branch_id) else f"Branch {inv.branch_id}",
                "invoice_count": 0,
                "total_sales": 0,
                "total_paid": 0,
                "total_balance": 0,
            })
            bucket["invoice_count"] += 1
            bucket["total_sales"] += inv.grand_total
            bucket["total_paid"] += inv.paid_amount
            bucket["total_balance"] += inv.balance

        items = [buckets[key] for key in sorted(buckets)]
        return {
            "date_from": str(date_from),
            "date_to": str(date_to),
            "branch_id": branch_id,
            "items": items,
            "total_invoices": sum(item["invoice_count"] for item in items),
            "total_sales": sum(item["total_sales"] for item in items),
            "total_paid": sum(item["total_paid"] for item in items),
            "total_balance": sum(item["total_balance"] for item in items),
        }

    @staticmethod
    def _resolve_local_tile_price(product, grade):
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT rate_per_meter FROM product_rate_overrides WHERE product_id = ? AND grade = ? AND COALESCE(active, 1) = 1",
                (product.id, grade),
            )
            row = cursor.fetchone()
            if not row:
                cursor.execute(
                    "SELECT rate_per_meter FROM tile_rates WHERE tile_size = ? AND grade = ? AND COALESCE(active, 1) = 1",
                    (product.tile_size, grade),
                )
                row = cursor.fetchone()
            if not row:
                return None
            rate_per_sqm = float(row[0])
            rate_per_box = rate_per_sqm * float(product.area_per_box)
            return {
                "rate_per_sqm": rate_per_sqm,
                "rate_per_box": rate_per_box,
                "rate_per_piece": rate_per_box / int(product.pieces_per_box),
            }
        except Exception:
            return None
        finally:
            conn.close()

