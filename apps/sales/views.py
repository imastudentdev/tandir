from django.views.generic import TemplateView, CreateView, ListView
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages
from django.db.models import Sum, Q
from apps.expenses.models import Expense, ExpenseCategory
from apps.production.models import SellerStock, ProductStock
from apps.users.mixins import SalesAccessRequiredMixin
from .models import Sale, DebtPayment
from .services import SalesService
import json
import logging
from django.utils import timezone
from django.db import transaction
from decimal import Decimal

logger = logging.getLogger(__name__)

class POSDashboardView(LoginRequiredMixin, SalesAccessRequiredMixin, TemplateView):
    """Sotuvchi va Menejer uchun moslashuvchan Kassa Terminali"""
    template_name = "sales/pos.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'baker':
            messages.error(request, "⚠️ Siz nonvoy rolidasiz! Sotuv terminaliga kirish huquqingiz yo'q.")
            return redirect('production:plan_list')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        products_data = []

        if user.role in ['admin', 'manager']:
            stocks = ProductStock.objects.filter(quantity__gt=0).select_related('product').prefetch_related('product__prices__price_type')
            context['source_type'] = "Asosiy Ombor (Ulgurji/To'g'ridan-to'g'ri)"
            context['is_direct_warehouse_sale'] = True
        else:
            stocks = SellerStock.objects.filter(seller=user, quantity__gt=0).select_related('product').prefetch_related('product__prices__price_type')
            context['source_type'] = "Sizning Vitrinangiz"
            context['is_direct_warehouse_sale'] = False

        for stock in stocks:
            product = stock.product
            prices_dict = {p_price.price_type.name: float(p_price.price) for p_price in product.prices.all()}

            if "Do'kon" not in prices_dict: prices_dict["Do'kon"] = 0.0
            if "To'yxona" not in prices_dict: prices_dict["To'yxona"] = 0.0

            products_data.append({
                'id': product.id,
                'name': product.name,
                'sku': product.sku if product.sku else f"P-{product.id}",
                'stock_qty': stock.quantity,
                'prices': prices_dict,
                'image_url': product.image.url if hasattr(product, 'image') and product.image else "/static/images/default_bread.png"
            })

        context['pos_products_json'] = json.dumps(products_data)
        context['total_vitrina_count'] = len(products_data)
        context['current_server_time'] = timezone.now().strftime("%Y-%m-%d %H:%M")
        return context

    
@transaction.atomic
def delete_or_fix_sale_view(request, sale_id):
    """Vazvrat qilish: Sotuvni bekor qilish va tovarlarni (Ombor yoki Vitrina) balansiga qaytarish"""
    if not request.user.is_authenticated:
        return redirect('users:login')

    if request.user.role == 'baker':
        messages.error(request, "⚠️ Nonvoylar sotuv amaliyotlarini o'chira olmaydi!")
        return redirect('production:plan_list')

    if request.user.role == 'admin':
        sale = get_object_or_404(Sale, id=sale_id)
    else:
        sale = get_object_or_404(Sale, id=sale_id, seller=request.user)
        
    for item in sale.items.all():
        if sale.seller.role in ['admin', 'manager']:
            p_stock, _ = ProductStock.objects.get_or_create(product=item.product)
            p_stock.quantity += item.quantity
            p_stock.save()
        else:
            s_stock, _ = SellerStock.objects.get_or_create(seller=sale.seller, product=item.product)
            s_stock.quantity += item.quantity
            s_stock.save()

    sale.delete()
    messages.success(request, f"🔄 #{sale_id}-sonli xarid bekor qilindi (Vazvrat). Tovar vitrinaga qaytdi!")
    return redirect('sales:seller_report')


class ProcessPOSSaleView(LoginRequiredMixin, SalesAccessRequiredMixin, CreateView):
    """POS terminaldan yuborilgan ma'lumotlarni qabul qilib bazani oily qatlamda yangilovchi Controller"""
    model = Sale
    fields = ['customer_name', 'customer_phone', 'payment_type']

    def post(self, request, *args, **kwargs):
        c_name = request.POST.get('customer_name')
        c_phone = request.POST.get('customer_phone')
        p_type = request.POST.get('payment_type')
        cart_json = request.POST.get('cart_data_json')

        try:
            cart_data = json.loads(cart_json) if cart_json else []
            if not cart_data:
                messages.error(request, "❌ Savatcha bo'sh! Sotuv amalga oshmadi.")
                return redirect('sales:pos_dashboard')
                
            sale = SalesService.create_sale(
                seller=request.user,
                customer_name=c_name,
                customer_phone=c_phone,
                payment_type=p_type,
                cart_data=cart_data
            )
            messages.success(request, f"🚀 Sotuv yakunlandi! Chek #{sale.id}")
        
        except Exception as e:
            logger.error(f"--- SOTUV XATOLIGI --- {str(e)}")
            messages.error(request, f"Sotuv amalga oshmadi: {str(e)}")

        return redirect('sales:pos_dashboard')
    

class SellerReportView(LoginRequiredMixin, SalesAccessRequiredMixin, ListView):
    """Sotuvchilar, Menejer va Admin uchun sotuvlar va kassa balansi"""
    template_name = "sales/seller_report.html"
    context_object_name = "sales"
    paginate_by = 20

    def get_queryset(self):
        if self.request.user.role == 'admin':
            queryset = Sale.objects.all().order_by('-created_at')
        else:
            queryset = Sale.objects.filter(seller=self.request.user).order_by('-created_at')

        search_query = self.request.GET.get('search', '')
        payment_filter = self.request.GET.get('payment_type', '')
        date_filter = self.request.GET.get('date_range', 'today')

        if search_query:
            queryset = queryset.filter(
                Q(customer_name__icontains=search_query) | 
                Q(customer_phone__icontains=search_query)
            )

        if payment_filter in ['cash', 'debt']:
            queryset = queryset.filter(payment_type=payment_filter)

        now = timezone.now()
        if date_filter == 'today':
            queryset = queryset.filter(created_at__date=now.date())
        elif date_filter == 'yesterday':
            queryset = queryset.filter(created_at__date=now.date() - timezone.timedelta(days=1))
        elif date_filter == 'week':
            queryset = queryset.filter(created_at__gte=now - timezone.timedelta(days=7))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        
        context['current_search'] = self.request.GET.get('search', '')
        context['current_payment'] = self.request.GET.get('payment_type', '')
        context['current_date'] = self.request.GET.get('date_range', 'today')

        if self.request.user.role == 'admin':
            base_stats = Sale.objects.all()
        else:
            base_stats = Sale.objects.filter(seller=self.request.user)
        
        if context['current_date'] == 'today':
            base_stats = base_stats.filter(created_at__date=now.date())
        elif context['current_date'] == 'yesterday':
            base_stats = base_stats.filter(created_at__date=now.date() - timezone.timedelta(days=1))
        elif context['current_date'] == 'week':
            base_stats = base_stats.filter(created_at__gte=now - timezone.timedelta(days=7))

        context['total_cash'] = base_stats.filter(payment_type='cash').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        context['total_debt'] = base_stats.filter(payment_type='debt').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        context['grand_total'] = context['total_cash'] + context['total_debt']
        
        return context


class StaffExpenseCreateView(LoginRequiredMixin, SalesAccessRequiredMixin, CreateView):
    """Xodimlarning kunlik shaxsiy/ish yo'li xarajatlarini kiritish oynasi"""
    model = Expense
    fields = ['category', 'amount', 'comment']
    template_name = "expenses/staff_expense_form.html"
    success_url = reverse_lazy('sales:seller_report')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Kunlik xarajat muvaffaqiyatli qayd etildi.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ExpenseCategory.objects.all()
        return context
    

class DebtManagementView(LoginRequiredMixin, SalesAccessRequiredMixin, ListView):
    """Nasiyalarni kuzatish paneli"""
    model = Sale
    template_name = "sales/debts.html"
    context_object_name = "debts"

    def get_queryset(self):
        if self.request.user.role in ['admin', 'manager']:
            return Sale.objects.filter(payment_type='debt', debt_status='unpaid').order_by('-created_at')
        return Sale.objects.filter(seller=self.request.user, payment_type='debt', debt_status='unpaid').order_by('-created_at')


def pay_debt_partially_view(request, sale_id):
    """Qarzning ma'lum bir qismini xavfsiz ayirish funksiyasi"""
    if not request.user.is_authenticated:
        return redirect('users:login')

    if request.user.role == 'baker':
        messages.error(request, "⚠️ Nonvoylar qarz hisobotlari bilan ishlay olmaydi!")
        return redirect('production:plan_list')

    if request.method == "POST":
        raw_amount = request.POST.get('amount', '0').replace(' ', '').replace(',', '')
        try:
            amount_paid = Decimal(raw_amount)
        except:
            messages.error(request, "❌ To'lov miqdori noto'g'ri kiritildi!")
            return redirect('sales:debt_dashboard')
        
        with transaction.atomic():
            sale = get_object_or_404(Sale, id=sale_id, payment_type='debt')
            
            if not sale.remaining_debt or sale.remaining_debt == 0:
                sale.remaining_debt = sale.total_amount
            
            remaining = Decimal(str(sale.remaining_debt))
            
            if amount_paid <= 0:
                messages.error(request, "⚠️ To'lov miqdori noldan katta bo'lishi kerak!")
                return redirect('sales:debt_dashboard')
                
            if amount_paid > remaining:
                messages.error(request, f"⚠️ Ortiqcha pul kiritildi! Maksimal qarz: {remaining:,.0f} so'm")
                return redirect('sales:debt_dashboard')

            sale.remaining_debt = remaining - amount_paid
            
            if sale.remaining_debt <= 0:
                sale.debt_status = 'paid'
            sale.save()
            
            DebtPayment.objects.create(
                sale=sale,
                collected_by=request.user,
                amount_paid=amount_paid
            )
            messages.success(request, f"💳 {sale.customer_name} qarzidan {amount_paid:,.0f} so'm muvaffaqiyatli ayrildi.")
            
    return redirect('sales:debt_dashboard')


class RequestStockView(LoginRequiredMixin, SalesAccessRequiredMixin, View):
    """Sotuvchi uchun asosiy ombordan o'z vitrinasiga non ajratib olish formasi"""
    template_name = "sales/request_stock.html"

    def get(self, request):
        warehouse_stock = ProductStock.objects.filter(quantity__gt=0).select_related('product')
        return render(request, self.template_name, {'warehouse_stock': warehouse_stock})

    @transaction.atomic
    def post(self, request):
        product_id = request.POST.get('product_id')
        requested_qty = int(request.POST.get('quantity', 0))

        if requested_qty <= 0:
            messages.error(request, "⚠️ Miqdor noldan katta bo'lishi kerak!")
            return redirect('sales:request_stock')

        p_stock = get_object_or_404(ProductStock, product_id=product_id)
        if p_stock.quantity < requested_qty:
            messages.error(request, f"❌ Omborda yetarli mahsulot yo'q! Maksimal qoldiq: {p_stock.quantity} ta")
            return redirect('sales:request_stock')

        p_stock.quantity -= requested_qty
        p_stock.save()

        s_stock, created = SellerStock.objects.get_or_create(
            seller=request.user,
            product_id=product_id,
            defaults={'quantity': 0}
        )
        s_stock.quantity += requested_qty
        s_stock.save()

        messages.success(request, f"✅ Ombordan {s_stock.product.name} mahsulotidan {requested_qty} ta muvaffaqiyatli vitrinangizga olindi!")
        return redirect('sales:pos_dashboard')

    
class ReturnStockToWarehouseView(LoginRequiredMixin, SalesAccessRequiredMixin, View):
    """Sotuvchi o'z vitrinasidagi tovarlarni asosiy omborga qaytarishi (Vazvrat)"""
    template_name = "sales/return_stock.html"

    def get(self, request):
        seller_stock = SellerStock.objects.filter(seller=request.user, quantity__gt=0).select_related('product')
        return render(request, self.template_name, {'seller_stock': seller_stock})

    @transaction.atomic
    def post(self, request):
        product_id = request.POST.get('product_id')
        return_qty = int(request.POST.get('quantity', 0))

        if return_qty <= 0:
            messages.error(request, "⚠️ Miqdor noldan katta bo'lishi kerak!")
            return redirect('sales:return_stock')

        s_stock = get_object_or_404(SellerStock, seller=request.user, product_id=product_id)
        if s_stock.quantity < return_qty:
            messages.error(request, f"❌ Vitrinangizda buncha mahsulot yo'q! Maksimal qoldiq: {s_stock.quantity} ta")
            return redirect('sales:return_stock')

        s_stock.quantity -= return_qty
        if s_stock.quantity == 0:
            s_stock.delete()
        else:
            s_stock.save()

        p_stock, created = ProductStock.objects.get_or_create(
            product_id=product_id,
            defaults={'quantity': 0}
        )
        p_stock.quantity += return_qty
        p_stock.save()

        messages.success(request, f"🔄 {s_stock.product.name} mahsulotidan {return_qty} tasi asosiy omborga muvaffaqiyatli qaytarildi!")
        return redirect('sales:pos_dashboard')