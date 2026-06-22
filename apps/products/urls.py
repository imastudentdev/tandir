from django.urls import path
from .views import ProductListView, ProductCreateView, ProductUpdateView, PriceTypeManageView

app_name = 'products'

urlpatterns = [
    path('', ProductListView.as_view(), name='product_list'),
    path('create/', ProductCreateView.as_view(), name='product_create'),
    path('<int:pk>/edit/', ProductUpdateView.as_view(), name='product_edit'),
    path('price-types/', PriceTypeManageView.as_view(), name='pricetype_manage'),
]