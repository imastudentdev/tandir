from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.users.mixins import AdminRequiredMixin
from apps.sales.models import Sale
from apps.expenses.models import Expense
from apps.inventory.models import IngredientBatch
from django.db.models import Sum
from decimal import Decimal

class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Biznes egasi uchun jami tushum, xarajat va sof foyda tahlili paneli"""
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. JAMI TUSHUM (Sotuvlar summasi)
        # Izoh: Order modelidagi jami summani hisoblaymiz
        total_sales = Sale.objects.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        # 2. JAMI CHIQIM (Xarajatlar summasi)
        total_expenses = Expense.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # 3. XOMASHYO SOTIB OLISH XARAJATLARI (Ombor tannarxi)
        # Biznesda foydani aniq bilish uchun un va boshqa xomashyoga ketgan pul ham xarajatga qo'shiladi
        total_inventory_cost = IngredientBatch.objects.aggregate(
            total=Sum('initial_quantity') * Sum('purchase_price')
        )['total'] or Decimal('0.00')
        
        # Jami xarajatlar yig'indisi
        grand_total_expenses = total_expenses + total_inventory_cost

        # 4. SOF FOYDA KALKULYATSIYASI
        # Jami tushumdan barcha chiqimlar chegirib tashlanadi
        net_profit = total_sales - grand_total_expenses

        # Context'ga yuklash
        context['total_sales'] = total_sales
        context['total_expenses'] = grand_total_expenses
        context['net_profit'] = net_profit
        
        # Grafiklar uchun qisqacha ma'lumot (Masalan oxirgi 5 ta sotuv)
        context['recent_orders'] = Sale.objects.order_by('-created_at')[:5]
        
        return context