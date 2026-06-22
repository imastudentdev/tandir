import json
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.db.models import Sum, F, Q
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from apps.users.mixins import AdminRequiredMixin, SellerOrBakerRequiredMixin
from .models import ProductionPlan, ProductionRecord, ProductStock, SellerStock, ProductReturn
from .services import ProductionService
from apps.products.models import Product
from apps.users.models import CustomUser
from django.db import transaction

class ProductionPlanListView(SellerOrBakerRequiredMixin, ListView):
    """Novvoy va Adminlar uchun kunlik ishlab chiqarish rejalari va faktlar xulosasi"""
    model = ProductionPlan
    template_name = 'production/plan_list.html'
    context_object_name = 'plans'
    
    def get_queryset(self):
        # Faqat bugungi va faol rejalarni prefetch bilan optimallashgan holda oladi
        today = timezone.now().date()
        return ProductionPlan.objects.filter(
            created_at__date=today
        ).select_related('product').order_by('-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Bugungi jami reja va jami tayyorlangan nonlar statistikasi
        today_plans = self.get_queryset()
        context['total_planned'] = today_plans.aggregate(Sum('planned_quantity'))['planned_quantity__sum'] or 0
        
        # Novvoy joriy smenada qancha oylik ishlaganini ko'rishi uchun
        context['baker_today_earned'] = ProductionRecord.objects.filter(
            baker=self.request.user,
            created_at__date=timezone.now().date()
        ).aggregate(
            earned=Sum(F('actual_quantity') * F('product__worker_share'))
        )['earned'] or 0
        
        return context

class RecordProductionView(SellerOrBakerRequiredMixin, CreateView):
    """Novvoy reja ustiga bosganda yoki alohida fakt yozganda ishlovchi view"""
    model = ProductionRecord
    fields = ['plan', 'product', 'actual_quantity', 'waste_quantity']
    success_url = reverse_lazy('production:plan_list')

    def post(self, request, *args, **kwargs):
        product_id = request.POST.get('product')
        actual_qty = int(request.POST.get('actual_quantity', 0))
        waste_qty = int(request.POST.get('waste_quantity', 0))
        plan_id = request.POST.get('plan')

        if actual_qty <= 0 and waste_qty <= 0:
            messages.error(request, "⚠️ Tayyorlangan yoki brak non miqdori kiritilishi shart!")
            return redirect('production:plan_list')

        try:
            product = Product.objects.get(id=product_id)
            plan = ProductionPlan.objects.get(id=plan_id) if plan_id else None
            
            # Servis qatlami orqali omborga qo'shish va rejani yangilash
            ProductionService.record_production(
                product=product,
                actual_quantity=actual_qty,
                waste_quantity=waste_qty,
                baker=request.user,
                plan=plan
            )
            messages.success(request, f"🎉 {actual_qty} ta [{product.name}] omborga olindi. Brak: {waste_qty} ta.")
        except Exception as e:
            messages.error(request, f"❌ Xatolik: {str(e)}")
            
        return redirect('production:plan_list')

class SellerStockListView(SellerOrBakerRequiredMixin, ListView):
    """Vitrinalar qoldig'i - Admin barchasini, sotuvchi faqat o'zinikini ko'radi"""
    model = SellerStock
    template_name = 'production/vitrina_list.html'
    context_object_name = 'stocks'
    
    def get_queryset(self):
        qs = SellerStock.objects.select_related('seller', 'product')
        if self.request.user.role == 'seller':
            return qs.filter(seller=self.request.user)
        return qs.order_by('seller', '-quantity')

def distribute_product_view(request):
    """Asosiy ombordan vitrinaga xavfsiz tarqatish (Ombor qoldig'i nazorati bilan)"""
    if not request.user.is_authenticated or request.user.role != 'admin':
        messages.error(request, "Sizda ushbu operatsiyani bajarish huquqi yo'q!")
        return redirect('production:vitrina_list')

    if request.method == "POST":
        product_id = request.POST.get('product')
        seller_id = request.POST.get('seller')
        quantity = int(request.POST.get('quantity', 0))

        try:
            product = Product.objects.get(id=product_id)
            seller = CustomUser.objects.get(id=seller_id)
            
            # Xavfsizlik: Asosiy omborda yetarli non bormi?
            stock = ProductStock.objects.filter(product=product).first()
            if not stock or stock.quantity < quantity:
                raise ValueError(f"Asosiy omborda yetarli mahsulot yo'q! Maksimal qoldiq: {stock.quantity if stock else 0} ta.")

            ProductionService.distribute_to_seller(product, seller, quantity)
            messages.success(request, f"🚚 {quantity} ta {product.name} -> {seller.get_full_name()} vitrinasiga muvaffaqiyatli o'tkazildi.")
            return redirect('production:vitrina_list')
        except Exception as e:
            messages.error(request, f"⚠️ Taqiqlangan harakat: {str(e)}")

    # Frontda Alpine.js cheklovlarni bilishi uchun JSON map shakllantiramiz
    stocks = ProductStock.objects.filter(quantity__gt=0).select_related('product')
    stock_map = {s.product.id: s.quantity for s in stocks}
    
    return render(request, 'production/distribute_form.html', {
        'products': stocks,
        'sellers': CustomUser.objects.filter(role='seller'),
        'stock_map_json': json.dumps(stock_map)
    })

def return_product_view(request):
    """Sotuvchi yoki admindan vozvrat (brak/ortib qolgan) nonlarni qabul qilish"""
    if not request.user.is_authenticated or request.user.role not in ['admin', 'seller']:
        messages.error(request, "Ruxsat berilmadi!")
        return redirect('production:vitrina_list')

    if request.method == "POST":
        product_id = request.POST.get('product')
        quantity = int(request.POST.get('quantity', 0))
        reason = request.POST.get('reason')
        seller_id = request.POST.get('seller')
        
        seller = CustomUser.objects.get(id=seller_id) if seller_id else request.user

        try:
            product = Product.objects.get(id=product_id)
            
            # Xavfsizlik: Sotuvchining vitrinasida rostdan ham o'sha non bormi?
            v_stock = SellerStock.objects.filter(seller=seller, product=product).first()
            if not v_stock or v_stock.quantity < quantity:
                raise ValueError(f"Sotuvchi vitrinasida bu miqdorda non mavjud emas! Maksimal: {v_stock.quantity if v_stock else 0} ta.")

            ProductionService.process_return(seller, product, quantity, reason)
            messages.success(request, f"🔄 Vozvrat qabul qilindi: {quantity} ta {product.name} ({reason}).")
            return redirect('production:vitrina_list')
        except Exception as e:
            messages.error(request, f"Xatolik: {str(e)}")

    # Faqat vitrinasida tovari bor sotuvchilarni ko'rsatish
    return render(request, 'production/return_form.html', {
        'products': Product.objects.all(),
        'sellers': CustomUser.objects.filter(role='seller'),
        'reasons': [('broken', 'Brak / Kul bo\'lgan'), ('surplus', 'Ortib qolgan (Sotilmagan)')]
    })

class BakerSalaryDashboardView(AdminRequiredMixin, ListView):
    """Faqat Admin ko'radigan yopilmagan smenalar va oyliklar balansi"""
    model = ProductionRecord
    template_name = "production/baker_salary.html"
    context_object_name = "records"

    def get_queryset(self):
        return ProductionRecord.objects.filter(is_salary_calculated=False).select_related('baker', 'product')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unpaid_salaries'] = ProductionRecord.objects.filter(
            is_salary_calculated=False
        ).values(
            'baker__id', 'baker__phone_number'
        ).annotate(
            full_name=F('baker__phone_number'), # Agar full_name bo'sh bo'lsa raqami
            total_bakes=Sum('actual_quantity'),
            total_earned=Sum(F('actual_quantity') * F('product__worker_share'))
        )
        return context
    

@transaction.atomic
def pay_baker_salary_view(request, baker_id):
    """Novvoyning shu vaqtgacha yopilmagan barcha smenadagi oyliklarini to'langan deb belgilash"""
    if not request.user.is_authenticated or request.user.role != 'admin':
        messages.error(request, "Sizda ushbu operatsiyani bajarish huquqi yo'q!")
        return redirect('production:baker_salary')

    if request.method == "POST":
        try:
            baker = get_object_or_404(CustomUser, id=baker_id)
            
            # Shu novvoyga tegishli va hali oyligi hisoblanmagan barcha yozuvlarni yangilash
            updated_count = ProductionRecord.objects.filter(
                baker=baker,
                is_salary_calculated=False
            ).update(is_salary_calculated=True)
            
            if updated_count > 0:
                messages.success(request, f"💰 {baker.get_full_name() or baker.phone_number} uchun oylik muvaffaqiyatli to'landi! ({updated_count} ta smena yopildi).")
            else:
                messages.warning(request, "Bu xodimda to'lanishi kerak bo'lgan oylik mavjud emas.")
                
        except Exception as e:
            messages.error(request, f"Xatolik yuz berdi: {str(e)}")
            
    return redirect('production:baker_salary')