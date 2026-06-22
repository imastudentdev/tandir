from django.urls import path
from .views import (
    ProductionPlanListView, RecordProductionView, SellerStockListView,
    distribute_product_view, return_product_view, BakerSalaryDashboardView, pay_baker_salary_view
)

app_name = 'production'

urlpatterns = [
    # Ishlab chiqarish (Reja va Fakt)
    path('plans/', ProductionPlanListView.as_view(), name='plan_list'),
    path('record-fakt/', RecordProductionView.as_view(), name='record_production'),
    
    # Vitrina (SellerStock) va Tarqatish/Qaytim
    path('vitrinas/', SellerStockListView.as_view(), name='vitrina_list'),
    path('distribute/', distribute_product_view, name='distribute_product'),
    path('returns/', return_product_view, name='return_product'),
    
    # Oylik hisob-kitoblari
    path('baker-salary/', BakerSalaryDashboardView.as_view(), name='baker_salary'),
    path('pay-salary/<int:baker_id>/', pay_baker_salary_view, name='pay_salary'),
]