from django.urls import path
from .views import (
    POSDashboardView, 
    SellerReportView, 
    StaffExpenseCreateView,
    ProcessPOSSaleView,
    DebtManagementView,
    RequestStockView,
    ReturnStockToWarehouseView,
    pay_debt_partially_view,
    delete_or_fix_sale_view
)

app_name = 'sales'

urlpatterns = [
    path('pos/', POSDashboardView.as_view(), name='pos_dashboard'),
    path('debts/', DebtManagementView.as_view(), name='debt_dashboard'),
    path('debts/pay/<int:sale_id>/', pay_debt_partially_view, name='pay_debt'),
    path('sale/delete/<int:sale_id>/', delete_or_fix_sale_view, name='delete_sale'),
    path('pos/process/', ProcessPOSSaleView.as_view(), name='process_sale'),
    path('pos/request-stock/', RequestStockView.as_view(), name='request_stock'),
    path('pos/return-stock/', ReturnStockToWarehouseView.as_view(), name='return_stock'),
    path('my-report/', SellerReportView.as_view(), name='seller_report'),
    path('staff-expense/add/', StaffExpenseCreateView.as_view(), name='add_staff_expense'),
]