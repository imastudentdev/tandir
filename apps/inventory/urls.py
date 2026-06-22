from django.urls import path
from .views import InventoryDashboardView, AddStockView

app_name = 'inventory'

urlpatterns = [
    path('', InventoryDashboardView.as_view(), name='dashboard'),
    path('add-stock/', AddStockView.as_view(), name='add_stock'),
]