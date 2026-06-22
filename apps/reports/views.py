from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from django.db.models import Sum, F
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from apps.users.mixins import AdminRequiredMixin
from apps.sales.models import Sale, SaleItem
from apps.expenses.models import Expense
from apps.production.models import ProductStock, SellerStock, ProductionRecord

class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Adminlar va Direktorlar uchun boshqaruv paneli (Moliyaviy hisobotlar va tahlillar)"""
    template_name = "dashboard/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        
        sales_query = Sale.objects.all()
        total_cash = sales_query.filter(payment_type='cash').aggregate(total=Sum('total_amount'))['total'] or 0
        total_debt = sales_query.filter(payment_type='debt').aggregate(total=Sum('total_amount'))['total'] or 0
        total_sales = total_cash + total_debt
        
        today_sales_cash = sales_query.filter(created_at__date=today, payment_type='cash').aggregate(total=Sum('total_amount'))['total'] or 0
        today_sales_debt = sales_query.filter(created_at__date=today, payment_type='debt').aggregate(total=Sum('total_amount'))['total'] or 0
        today_total_sales = today_sales_cash + today_sales_debt

        total_expenses = Expense.objects.aggregate(total=Sum('amount'))['total'] or 0
        today_expenses = Expense.objects.filter(date=today).aggregate(total=Sum('amount'))['total'] or 0

        net_profit = total_sales - total_expenses
        today_net_profit = today_total_sales - today_expenses

        low_main_stock = ProductStock.objects.filter(quantity__lt=50).select_related('product')
        low_seller_stock = SellerStock.objects.filter(quantity__lt=30).select_related('product', 'seller')

        top_debts = Sale.objects.filter(payment_type='debt').select_related('seller').order_by('-total_amount')[:5]

        top_products = SaleItem.objects.values('product__name').annotate(
            total_qty=Sum('quantity'),
            total_sum=Sum('subtotal')
        ).order_by('-total_qty')[:5]

        context.update({
            'total_cash': total_cash,
            'total_debt': total_debt,
            'total_sales': total_sales,
            'net_profit': net_profit,
            
            'today_total_sales': today_total_sales,
            'today_expenses': today_expenses,
            'today_net_profit': today_net_profit,
            
            'low_main_stock': low_main_stock,
            'low_seller_stock': low_seller_stock,
            'top_debts': top_debts,
            'top_products': top_products,
            'is_loss': net_profit < 0,
            'is_today_loss': today_net_profit < 0,
        })
        return context


class ExportSalesReportExcelView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Sotuvlar tarixini professional darajada Excel fayliga eksport qilish"""
    
    def get(self, request, *args, **kwargs):
        wb = Workbook()
        ws = wb.active
        ws.title = "Sotuvlar Hisoboti"
        
        ws.views.sheetView[0].showGridLines = True
        
        font_header = Font(name='Segoe UI', size=11, bold=True, color='FFFFFF')
        font_body = Font(name='Segoe UI', size=11)
        font_title = Font(name='Segoe UI', size=16, bold=True, color='1E3A8A')
        
        fill_header = PatternFill(start_color='1E3A8A', end_color='1E3A8A', fill_type='solid')
        fill_total = PatternFill(start_color='E2E8F0', end_color='E2E8F0', fill_type='solid')
        
        align_center = Alignment(horizontal='center', vertical='center')
        align_right = Alignment(horizontal='right', vertical='center')
        align_left = Alignment(horizontal='left', vertical='center')
        
        thin_border = Border(
            left=Side(style='thin', color='CBD5E1'),
            right=Side(style='thin', color='CBD5E1'),
            top=Side(style='thin', color='CBD5E1'),
            bottom=Side(style='thin', color='CBD5E1')
        )

        ws.merge_cells('A1:F1')
        ws['A1'] = "NONVOYXONA ERP TIZIMI - SOTUVLAR HISOBOTI"
        ws['A1'].font = font_title
        ws['A1'].alignment = align_center
        ws.row_dimensions[1].height = 40
        
        ws.append([])

        headers = ["Chek №", "Mijoz Ismi", "Mijoz Telefoni", "Sotuvchi (Kassir)", "To'lov turi", "Jami Summa (so'm)"]
        ws.append(headers)
        ws.row_dimensions[3].height = 25
        
        for col_num, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col_num)
            cell.font = font_header
            cell.fill = fill_header
            cell.alignment = align_center
            cell.border = thin_border

        sales = Sale.objects.all().select_related('seller').order_by('-id')
        row_num = 4
        total_sum = 0
        
        for sale in sales:
            row_data = [
                f"Chek #{sale.id}",
                sale.customer_name,
                sale.customer_phone,
                sale.seller.full_name or sale.seller.username,
                sale.get_payment_type_display(),
                sale.total_amount
            ]
            ws.append(row_data)
            total_sum += sale.total_amount
            
            ws.cell(row=row_num, column=1).alignment = align_center
            ws.cell(row=row_num, column=2).alignment = align_left
            ws.cell(row=row_num, column=3).alignment = align_center
            ws.cell(row=row_num, column=4).alignment = align_left
            ws.cell(row=row_num, column=5).alignment = align_center
            
            price_cell = ws.cell(row=row_num, column=6)
            price_cell.alignment = align_right
            price_cell.number_format = '#,##0.00'
            
            for col_num in range(1, 7):
                c = ws.cell(row=row_num, column=col_num)
                c.font = font_body
                c.border = thin_border
            
            ws.row_dimensions[row_num].height = 20
            row_num += 1

        ws.append(["JAMI SOTUV", "", "", "", "", total_sum])
        ws.merge_cells(start_row=row_num, start_column=1, end_row=row_num, end_column=5)
        
        total_label = ws.cell(row=row_num, column=1)
        total_label.font = Font(name='Segoe UI', size=11, bold=True)
        total_label.alignment = align_left
        
        total_val = ws.cell(row=row_num, column=6)
        total_val.font = Font(name='Segoe UI', size=11, bold=True)
        total_val.alignment = align_right
        total_val.number_format = '#,##0.00'
        
        for col_num in range(1, 7):
            c = ws.cell(row=row_num, column=col_num)
            c.fill = fill_total
            c.border = thin_border
            
        ws.row_dimensions[row_num].height = 25

        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column) 
            for cell in col:
                if cell.row == 1:
                    continue
                if cell.value:
                    max_len = max(max_len, len(str(cell.value)))
            ws.column_dimensions[col_letter].width = max(max_len + 4, 15)

        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        filename = f"Sotuvlar_Hisoboti_{timezone.now().strftime('%Y-%m-%d')}.xlsx"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        
        return response