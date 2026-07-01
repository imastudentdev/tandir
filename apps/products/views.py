from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from apps.users.mixins import AdminOrManagerRequiredMixin
from .models import Product, PriceType, ProductPrice

class ProductListView(ListView):
    """Barcha mahsulotlar ro'yxati (Ular uchun narxlari bilan birga)"""
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    
    def get_queryset(self):
        return Product.objects.all().prefetch_related('prices__price_type')

class ProductCreateView(AdminOrManagerRequiredMixin, CreateView):
    """Yangi tayyor mahsulot qo'shish"""
    model = Product
    fields = ['name', 'sku', 'image', 'is_active', 'worker_share']
    template_name = 'products/product_form.html'
    success_url = reverse_lazy('products:product_list')

    def form_valid(self, form):
        messages.success(self.request, "Yangi mahsulot yaratildi. Endi unga narx belgilashingiz mumkin.")
        return super().form_valid(form)

class ProductUpdateView(AdminOrManagerRequiredMixin, UpdateView):
    """Mahsulot tahrirlash"""
    model = Product
    fields = ['name', 'sku', 'image', 'is_active', 'worker_share']
    template_name = 'products/product_form.html'
    success_url = reverse_lazy('products:product_list')

    def form_valid(self, form):
        messages.success(self.request, "Mahsulot ma'lumotlari tahrirlandi.")
        return super().form_valid(form)

class PriceTypeManageView(AdminOrManagerRequiredMixin, CreateView, ListView):
    """Narx turlarini (Do'kon, To'yxona...) yaratish va ro'yxatini ko'rish"""
    model = PriceType
    fields = ['name', 'description']
    template_name = 'products/pricetype_manage.html'
    success_url = reverse_lazy('products:pricetype_manage')
    context_object_name = 'pricetypes'

    def form_valid(self, form):
        messages.success(self.request, "Yangi narx turi qo'shildi.")
        return super().form_valid(form)