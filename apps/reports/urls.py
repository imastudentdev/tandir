from django.urls import path
from .views import AdminDashboardView, ExportSalesReportExcelView

app_name = 'reports'

urlpatterns = [
    path('dashboard/', AdminDashboardView.as_view(), name='dashboard'),
    path('export/sales/', ExportSalesReportExcelView.as_view(), name='export_sales_excel'),
]