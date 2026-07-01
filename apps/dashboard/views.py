from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.users.mixins import AdminOrManagerRequiredMixin
from django.db.models import Sum, F
from decimal import Decimal
from apps.expenses.models import Expense
from apps.sales.models import Sale
from apps.inventory.models import IngredientBatch

class AdminDashboardView(LoginRequiredMixin, AdminOrManagerRequiredMixin, TemplateView):
    """Biznes egasi uchun jami tushum, xarajat va sof foyda tahlili paneli"""
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        total_sales = Sale.objects.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        total_expenses = Expense.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        total_inventory_cost = IngredientBatch.objects.aggregate(
            total=Sum(F('initial_quantity') * F('purchase_price'))
        )['total'] or Decimal('0.00')
        
        grand_total_expenses = total_expenses + total_inventory_cost
        net_profit = total_sales - grand_total_expenses

        context['total_sales'] = total_sales
        context['total_expenses'] = grand_total_expenses
        context['net_profit'] = net_profit
        context['recent_orders'] = Sale.objects.order_by('-created_at')[:5]
        
        return context