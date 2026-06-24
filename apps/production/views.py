import json
from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.db.models import Sum, F, Q
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from apps.users.mixins import AdminRequiredMixin, SellerOrBakerRequiredMixin
from .models import ProductionRecord, ProductStock, SellerStock, ProductReturn
from .services import ProductionService
from apps.products.models import Product
from apps.users.models import CustomUser
from django.db import transaction

class ProductionHistoryListView(SellerOrBakerRequiredMixin, ListView):
    """Kiritilgan kunlik ishlab chiqarish faktlari ro'yxati va nonvoy oylik xulosasi"""
    model = ProductionRecord
    template_name = 'production/plan_list.html' # Fayl nomini o'zgartirmaslik uchun shunday qoldirdim
    context_object_name = 'records'
    
    def get_queryset(self):
        today = timezone.now().date()
        qs = ProductionRecord.objects.filter(created_at__date=today).select_related('product', 'baker')
        if self.request.user.role == 'baker':
            return qs.filter(baker=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.filter(recipe__isnull=False) # Faqat retsepti bor mahsulotlar
        
        # Bugun jami yopilgan nonlar soni (Fakt)
        context['total_actual_baked'] = self.get_queryset().aggregate(Sum('actual_quantity'))['actual_quantity__sum'] or 0
        
        # Nonvoy joriy smenada qancha oylik ishlaganini ko'rishi uchun
        context['baker_today_earned'] = ProductionRecord.objects.filter(
            baker=self.request.user,
            created_at__date=timezone.now().date()
        ).aggregate(
            earned=Sum(F('actual_quantity') * F('product__worker_share'))
        )['earned'] or 0
        
        return context

class RecordProductionView(SellerOrBakerRequiredMixin, CreateView):
    """Nonvoy tayyor mahsulotni to'g'ridan to'g'ri omborga kiritish oynasi"""
    model = ProductionRecord
    fields = ['product', 'actual_quantity', 'waste_quantity']
    success_url = reverse_lazy('production:plan_list')

    def post(self, request, *args, **kwargs):
        product_id = request.POST.get('product')
        actual_qty = int(request.POST.get('actual_quantity', 0))
        waste_qty = int(request.POST.get('waste_quantity', 0))

        if actual_qty <= 0:
            messages.error(request, "⚠️ Tayyorlangan non miqdori kiritilishi shart!")
            return redirect('production:plan_list')

        try:
            product = Product.objects.get(id=product_id)
            ProductionService.record_production(
                product=product,
                actual_quantity=actual_qty,
                waste_quantity=waste_qty,
                baker=request.user
            )
            messages.success(request, f"🎉 {actual_qty} ta [{product.name}] to'g'ridan-to'g'ri omborga qabul qilindi.")
        except Exception as e:
            messages.error(request, f"❌ Xatolik: {str(e)}")
            
        return redirect('production:plan_list')

def delete_production_record_view(request, record_id):
    """Kiritilgan faktni o'chirish va omborni qayta tiklash amali"""
    if request.method == "POST":
        try:
            ProductionService.delete_production_record(record_id)
            messages.success(request, "🗑️ Xato kiritilgan partiya o'chirildi va ombor qayta tiklandi.")
        except Exception as e:
            messages.error(request, f"❌ O'chirishda xatolik: {str(e)}")
    return redirect('production:plan_list')


# QOLGAN VITRINA VA OYLIK VIEW-LARI O'ZGARISHSIZ QOLADI
class SellerStockListView(SellerOrBakerRequiredMixin, ListView):
    model = SellerStock
    template_name = 'production/vitrina_list.html'
    context_object_name = 'stocks'
    
    def get_queryset(self):
        qs = SellerStock.objects.select_related('seller', 'product')
        if self.request.user.role == 'seller':
            return qs.filter(seller=self.request.user)
        return qs.order_by('seller', '-quantity')

def distribute_product_view(request):
    if not request.user.is_authenticated or request.user.role != 'admin':
        messages.error(request, "Ruxsat yo'q!")
        return redirect('production:vitrina_list')

    if request.method == "POST":
        product_id = request.POST.get('product')
        seller_id = request.POST.get('seller')
        quantity = int(request.POST.get('quantity', 0))
        try:
            product = Product.objects.get(id=product_id)
            seller = CustomUser.objects.get(id=seller_id)
            ProductionService.distribute_to_seller(product, seller, quantity)
            messages.success(request, f"🚚 {quantity} ta {product.name} vitrinaga o'tkazildi.")
            return redirect('production:vitrina_list')
        except Exception as e:
            messages.error(request, f"⚠️ Xatolik: {str(e)}")

    stocks = ProductStock.objects.filter(quantity__gt=0).select_related('product')
    stock_map = {s.product.id: s.quantity for s in stocks}
    return render(request, 'production/distribute_form.html', {
        'products': stocks,
        'sellers': CustomUser.objects.filter(role='seller'),
        'stock_map_json': json.dumps(stock_map)
    })

def return_product_view(request):
    if request.method == "POST":
        product_id = request.POST.get('product')
        quantity = int(request.POST.get('quantity', 0))
        reason = request.POST.get('reason')
        seller_id = request.POST.get('seller')
        seller = CustomUser.objects.get(id=seller_id) if seller_id else request.user
        try:
            product = Product.objects.get(id=product_id)
            ProductionService.process_return(seller, product, quantity, reason)
            messages.success(request, f"🔄 Vozvrat qabul qilindi.")
            return redirect('production:vitrina_list')
        except Exception as e:
            messages.error(request, f"Xatolik: {str(e)}")

    return render(request, 'production/return_form.html', {
        'products': Product.objects.all(),
        'sellers': CustomUser.objects.filter(role='seller'),
        'reasons': [('broken', 'Brak / Kul bo\'lgan'), ('surplus', 'Ortib qolgan'), ('back_to_stock', 'Asosiy omborga qaytarish')]
    })

class BakerSalaryDashboardView(AdminRequiredMixin, ListView):
    model = ProductionRecord
    template_name = "production/baker_salary.html"
    context_object_name = "records"

    def get_queryset(self):
        return ProductionRecord.objects.filter(is_salary_calculated=False).select_related('baker', 'product')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unpaid_salaries'] = ProductionRecord.objects.filter(
            is_salary_calculated=False
        ).values('baker__id', 'baker__phone_number').annotate(
            total_bakes=Sum('actual_quantity'),
            total_earned=Sum(F('actual_quantity') * F('product__worker_share'))
        )
        return context

@transaction.atomic
def pay_baker_salary_view(request, baker_id):
    if request.method == "POST" and request.user.role == 'admin':
        baker = get_object_or_404(CustomUser, id=baker_id)
        ProductionRecord.objects.filter(baker=baker, is_salary_calculated=False).update(is_salary_calculated=True)
        messages.success(request, f"💰 Oyliklar to'landi.")
    return redirect('production:baker_salary')