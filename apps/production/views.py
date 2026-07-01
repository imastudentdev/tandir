import json
from django.views.generic import ListView, CreateView, UpdateView, FormView
from django.urls import reverse_lazy
from django.db.models import Sum, F, Q
from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import PermissionDenied
from apps.users.mixins import AdminOrManagerRequiredMixin, BakerOnlyRequiredMixin, SalesAccessRequiredMixin
from .models import ProductionRecord, ProductStock, SellerStock, ProductReturn
from .services import ProductionService
from apps.products.models import Product
from apps.users.models import CustomUser
from apps.expenses.models import Expense, ExpenseCategory
from datetime import datetime, timedelta


class ProductionHistoryListView(ListView):
    """Kiritilgan kunlik ishlab chiqarish faktlari ro'yxati va nonvoy oylik xulosasi"""
    model = ProductionRecord
    template_name = 'production/plan_list.html'
    context_object_name = 'records'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        if request.user.role not in ['baker', 'admin', 'manager']:
            messages.error(request, "⚠️ Bu sahifani ko'rish uchun huquqingiz yetarli emas!")
            return redirect('sales:pos_dashboard')
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        # Timezone muammosini hal qilish uchun kun boshlanishi va tugashini aniqlaymiz
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        # created_at__range orqali bugungi kun chegarasidagi barcha yozuvlarni olamiz
        qs = ProductionRecord.objects.filter(
            created_at__range=(today_start, today_end)
        ).select_related('product', 'baker')
        
        if self.request.user.role == 'baker':
            return qs.filter(baker=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.filter(recipe__isnull=False)
        
        # Bugungi queryset xavfsiz vaqt oralig'ida
        today_records = self.get_queryset()
        
        context['total_actual_baked'] = today_records.aggregate(Sum('actual_quantity'))['actual_quantity__sum'] or 0
        
        if self.request.user.role == 'baker':
            # Daromad hisoblashda ham to'g'ri filtrdan foydalanamiz
            context['baker_today_earned'] = today_records.aggregate(
                earned=Sum(F('actual_quantity') * F('product__worker_share'))
            )['earned'] or 0
        else:
            context['baker_today_earned'] = 0
            
        return context

class RecordProductionView(CreateView):
    """Nonvoy yoki Admin tayyor mahsulotni to'g'ridan to'g'ri omborga kiritish oynasi"""
    model = ProductionRecord
    fields = ['product', 'actual_quantity', 'waste_quantity']
    success_url = reverse_lazy('production:plan_list')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        if request.user.role not in ['baker', 'admin']:
            messages.error(request, "⚠️ Faqat nonvoylar yoki administratorlar ishlab chiqarishni qayd eta oladi!")
            return redirect('production:plan_list')
        return super().dispatch(request, *args, **kwargs)

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


@transaction.atomic
def delete_production_record_view(request, record_id):
    """Kiritilgan faktni o'chirish (Faqat Admin/Manager uchun)"""
    if not request.user.is_authenticated:
        return redirect('users:login')
        
    if request.user.role not in ['admin', 'manager']:
        messages.error(request, "⚠️ Bu amalni bajarish uchun huquqingiz yetarli emas!")
        return redirect('production:plan_list')

    if request.method == "POST":
        try:
            ProductionService.delete_production_record(record_id)
            messages.success(request, "🗑️ Xato kiritilgan partiya o'chirildi va ombor qayta tiklandi.")
        except Exception as e:
            messages.error(request, f"❌ O'chirishda xatolik: {str(e)}")
    return redirect('production:plan_list')


class SellerStockListView(SalesAccessRequiredMixin, ListView):
    """Vitrinalar qoldig'ini ko'rish oynasi"""
    model = SellerStock
    template_name = 'production/vitrina_list.html'
    context_object_name = 'stocks'
    
    def get_queryset(self):
        qs = SellerStock.objects.select_related('seller', 'product')
        if self.request.user.role == 'seller':
            return qs.filter(seller=self.request.user)
        return qs.order_by('seller', '-quantity')


class VitrinaTransferView(SalesAccessRequiredMixin, FormView):
    """Sotuvchi o'zi uchun Asosiy Ombordan non ajratib olishi yoki Admin/Menejer taqsimlashi"""
    template_name = "production/distribute_form.html"
    success_url = reverse_lazy('production:vitrina_list')

    def dispatch(self, request, *args, **kwargs):
        if request.user.role == 'baker':
            messages.error(request, "Nonvoylar ombordan non tarqata olmaydi yoki ajratolmaydi!")
            return redirect('production:vitrina_list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product_stocks = ProductStock.objects.filter(quantity__gt=0).select_related('product')
        context['products'] = product_stocks
        
        if self.request.user.role in ['admin', 'manager']:
            context['sellers'] = CustomUser.objects.filter(role='seller')
            context['is_admin_or_manager'] = True
        else:
            context['sellers'] = [self.request.user]
            context['is_admin_or_manager'] = False

        stock_map = {str(ps.product.id): ps.quantity for ps in product_stocks}
        context['stock_map_json'] = json.dumps(stock_map)
        return context

    def post(self, request, *args, **kwargs):
        product_id = request.POST.get('product')
        quantity = int(request.POST.get('quantity', 0))
        
        if request.user.role in ['admin', 'manager']:
            seller_id = request.POST.get('seller')
            seller = get_object_or_404(CustomUser, id=seller_id, role='seller')
        else:
            seller = request.user

        if quantity <= 0:
            messages.error(request, "❌ Miqdor noto'g'ri kiritildi!")
            return redirect('production:distribute_product')

        try:
            with transaction.atomic():
                p_stock = ProductStock.objects.select_for_update().get(product_id=product_id)
                
                if p_stock.quantity < quantity:
                    messages.error(request, f"⚠️ Omborda yetarli tovar yo'q! Maksimal qoldiq: {p_stock.quantity} ta")
                    return redirect('production:distribute_product')

                p_stock.quantity -= quantity
                p_stock.save()

                s_stock, created = SellerStock.objects.get_or_create(seller=seller, product_id=product_id)
                s_stock.quantity += quantity
                s_stock.save()

                messages.success(request, f"🚚 {p_stock.product.name} mahsulotidan {quantity} ta vitrinaga yuklandi.")
        except ProductStock.DoesNotExist:
            messages.error(request, "❌ Tanlangan mahsulot asosiy omborda mavjud emas!")
        except Exception as e:
            messages.error(request, f"❌ Kutilmagan xatolik yuz berdi: {str(e)}")

        return redirect(self.success_url)


class ReturnProductView(SalesAccessRequiredMixin, FormView):
    """Sotuvchi o'z vitrinasi yoki Admin barcha vitrinadan vozvrat olish oynasi"""
    template_name = 'production/return_form.html'
    success_url = reverse_lazy('production:vitrina_list')

    def get(self, request, *args, **kwargs):
        if request.user.role in ['admin', 'manager']:
            active_stocks = SellerStock.objects.filter(quantity__gt=0).select_related('product', 'seller')
            sellers = CustomUser.objects.filter(role='seller')
        else:
            active_stocks = SellerStock.objects.filter(seller=request.user, quantity__gt=0).select_related('product')
            sellers = [request.user]

        vitrina_stock_map = {}
        for stock in SellerStock.objects.filter(quantity__gt=0):
            vitrina_stock_map[f"{stock.seller.id}_{stock.product.id}"] = stock.quantity

        return render(request, self.template_name, {
            'active_stocks': active_stocks,
            'sellers': sellers,
            'vitrina_stock_map_json': json.dumps(vitrina_stock_map),
            'reasons': [
                ('broken', "Brak / Yaroqsiz bo'lgan non"), 
                ('surplus', 'Ortib qolgan non (Sotilmagan)'), 
                ('back_to_stock', 'Asosiy omborga qaytarish')
            ]
        })

    def post(self, request, *args, **kwargs):
        product_id = request.POST.get('product')
        quantity = int(request.POST.get('quantity', 0))
        reason = request.POST.get('reason')
        
        if request.user.role in ['admin', 'manager']:
            seller_id = request.POST.get('seller')
            seller = get_object_or_404(CustomUser, id=seller_id)
        else:
            seller = request.user

        if quantity <= 0:
            messages.error(request, "Miqdor xato kiritildi!")
            return redirect('production:vitrina_list')

        try:
            product = Product.objects.get(id=product_id)
            with transaction.atomic():
                s_stock = SellerStock.objects.select_for_update().get(seller=seller, product=product)
                if s_stock.quantity < quantity:
                    messages.error(request, f"❌ Vitrinada yetarli qoldiq yo'q! Maksimal: {s_stock.quantity} ta")
                    return redirect('production:vitrina_list')
                
                ProductionService.process_return(seller, product, quantity, reason)
                messages.success(request, f"🔄 {quantity} ta {product.name} uchun vozvrat muvaffaqiyatli yakunlandi.")
        except SellerStock.DoesNotExist:
            messages.error(request, "❌ Bu mahsulot vitrinada umuman mavjud emas!")
        except Exception as e:
            messages.error(request, f"Xatolik: {str(e)}")

        return redirect(self.success_url)


class BakerSalaryDashboardView(AdminOrManagerRequiredMixin, ListView):
    """Nonvoylar oyligi va hisob-kitoblar paneli (Faqat Admin/Manager)"""
    model = ProductionRecord
    template_name = "production/baker_salary.html"
    context_object_name = "records"

    def get_queryset(self):
        return ProductionRecord.objects.filter(is_salary_calculated=False).select_related('baker', 'product')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unpaid_salaries'] = ProductionRecord.objects.filter(
            is_salary_calculated=False
        ).values('baker__id', 'baker__phone_number', 'baker__first_name', 'baker__last_name').annotate(
            total_bakes=Sum('actual_quantity'),
            total_earned=Sum(F('actual_quantity') * F('product__worker_share'))
        )
        return context


@transaction.atomic
def pay_baker_salary_view(request, baker_id):
    """Nonvoy oyliklarini yopish va avtomatik Xarajatlar (Expense) jadvaliga yozish amali"""
    if not request.user.is_authenticated:
        return redirect('users:login')
        
    if request.user.role != 'admin':
        messages.error(request, "⚠️ Oylik to'lovlarini faqat tizim Administratori tasdiqlay oladi!")
        return redirect('production:plan_list')

    if request.method == "POST":
        baker = get_object_or_404(CustomUser, id=baker_id)
        
        unpaid_records = ProductionRecord.objects.filter(baker=baker, is_salary_calculated=False).select_related('product')
        total_salary_amount = sum(record.actual_quantity * record.product.worker_share for record in unpaid_records)
        
        if total_salary_amount > 0:
            ProductionRecord.objects.filter(baker=baker, is_salary_calculated=False).update(is_salary_calculated=True)
            
            category, _ = ExpenseCategory.objects.get_or_create(
                name="Oylik (Ishbay haq)", 
                defaults={'description': "Xodimlarga to'lanadigan ishbay oylik maoshlari"}
            )
            
            Expense.objects.create(
                category=category,
                amount=total_salary_amount,
                comment=f"Nonvoy: {baker.get_full_name() or baker.phone_number} uchun ishbay oylik to'lovi yopildi.",
                created_by=request.user
            )
            
            messages.success(request, f"💰 {baker.get_full_name() or baker.phone_number} ga {total_salary_amount:,.0f} so'm oylik muvaffaqiyatli to'landi.")
        else:
            messages.warning(request, "Bu xodimda to'lanmagan ishbay smenalar mavjud emas.")
            
    return redirect('production:baker_salary')