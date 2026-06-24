from django.urls import path
from .views import (
    ProductionHistoryListView, RecordProductionView, delete_production_record_view,
    SellerStockListView, distribute_product_view, return_product_view, 
    BakerSalaryDashboardView, pay_baker_salary_view
)

app_name = 'production'

urlpatterns = [
    # Ishlab chiqarish (Fakt kiritish va Tarix)
    path('plans/', ProductionHistoryListView.as_view(), name='plan_list'), # Name o'zgarmadi, template xato bermasligi uchun
    path('record-fakt/', RecordProductionView.as_view(), name='record_production'),
    path('delete-record/<int:record_id>/', delete_production_record_view, name='delete_record'),
    
    # Vitrina va Tarqatish
    path('vitrinas/', SellerStockListView.as_view(), name='vitrina_list'),
    path('distribute/', distribute_product_view, name='distribute_product'),
    path('returns/', return_product_view, name='return_product'),
    
    # Oyliklar
    path('baker-salary/', BakerSalaryDashboardView.as_view(), name='baker_salary'),
    path('pay-salary/<int:baker_id>/', pay_baker_salary_view, name='pay_salary'),
]