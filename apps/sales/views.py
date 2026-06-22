from django.views.generic import TemplateView, CreateView, ListView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Q
from apps.products.models import Product, PriceType
from apps.expenses.models import Expense, ExpenseCategory
from apps.production.models import SellerStock, ProductStock
from apps.users.mixins import SellerOrBakerRequiredMixin
from .models import Sale, SaleItem, DebtPayment
from .services import SalesService
import json
import logging
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)

class POSDashboardView(LoginRequiredMixin, SellerOrBakerRequiredMixin, TemplateView):
    """Novvoy va Sotuvchi uchun moslashuvchan Universal POS Terminal"""
    template_name = "sales/pos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        products_data = []

        # MANTIQLI FILTR: Novvoy to'g'ridan-to'g'ri Asosiy omborga, Sotuvchi esa o'z vitrinasiga qaraydi
        if user.role == 'baker':
            # prefetch_related('product__prices__price_type') orqali narxlarni bazadan bitta so'rovda tez yuklaymiz
            stocks = ProductStock.objects.filter(quantity__gt=0).select_related('product').prefetch_related('product__prices__price_type')
            context['source_type'] = "Asosiy Ombor (Novvoy Rejimsiz)"
        else:
            stocks = SellerStock.objects.filter(seller=user, quantity__gt=0).select_related('product').prefetch_related('product__prices__price_type')
            context['source_type'] = "Sizning Shaxsiy Vitrinangiz"

        # Ma'lumotlarni JS formatiga o'tkazish
        for stock in stocks:
            product = stock.product
            
            # 📌 DINAMIK NARXLARNI JAMLASH:
            # Mahsulotga tegishli hamma narxlarni {'Do'kon': 3000, 'To'yxona': 2500} ko'rinishiga keltiramiz
            prices_dict = {}
            for p_price in product.prices.all():
                prices_dict[p_price.price_type.name] = float(p_price.price)

            # Agar bazada biron bir narx turi kiritilmagan bo'lsa, xato bermasligi uchun default (0) qiymat beramiz
            if "Do'kon" not in prices_dict:
                prices_dict["Do'kon"] = 0.0
            if "To'yxona" not in prices_dict:
                prices_dict["To'yxona"] = 0.0

            products_data.append({
                'id': product.id,
                'name': product.name,
                'sku': product.sku if product.sku else f"P-{product.id}",
                'stock_qty': stock.quantity,
                'prices': prices_dict  # Endi xatolik butunlay yo'qoldi!
            })

        context['pos_products_json'] = json.dumps(products_data)
        return context
    
def delete_or_fix_sale_view(request, sale_id):
    """Sotuvchi xato qilgan sotuvini o'chirishi (tovar omborga/vitrinaga qaytadi)"""
    if not request.user.is_authenticated:
        return redirect('users:login')

    with transaction.atomic():
        sale = get_object_or_404(Sale, id=sale_id, seller=request.user)
        
        # Sotilgan tovarlarni qaytadan egasiga qaytarish logikasi
        for item in sale.items.all():
            if request.user.role == 'baker':
                # Novvoy sotgan bo'lsa - Asosiy omborga qaytadi
                p_stock, _ = ProductStock.objects.get_or_create(product=item.product)
                p_stock.quantity += item.quantity
                p_stock.save()
            else:
                # Sotuvchi sotgan bo'lsa - Shaxsiy vitrinaga qaytadi
                s_stock, _ = SellerStock.objects.get_or_create(seller=request.user, product=item.product)
                s_stock.quantity += item.quantity
                s_stock.save()

        sale.delete()
        messages.success(request, f"🔄 #{sale_id} - Sotuv xatoligi sababli bekor qilindi, tovarlar qoldiqqa qaytarildi!")
    
    return redirect('sales:seller_report')


class ProcessPOSSaleView(LoginRequiredMixin, CreateView):
    """POS terminaldan yuborilgan ma'lumotlarni qabul qilib bazani yangilovchi Controller"""
    model = Sale
    fields = ['customer_name', 'customer_phone', 'payment_type']

    def post(self, request, *args, **kwargs):
        c_name = request.POST.get('customer_name')
        c_phone = request.POST.get('customer_phone')
        p_type = request.POST.get('payment_type')
        cart_json = request.POST.get('cart_data_json')

        try:
            cart_data = json.loads(cart_json) if cart_json else []
            
            sale = SalesService.create_sale(
                seller=request.user,
                customer_name=c_name,
                customer_phone=c_phone,
                payment_type=p_type,
                cart_data=cart_data
            )
            messages.success(request, f"🚀 Sotuv yakunlandi! Baza yangilandi. Chek #{sale.id}")
        
        except Exception as e:
            logger.error(f"--- SOTUV XATOLIGI --- {str(e)}")
            messages.error(request, f"Sotuv amalga oshmadi: {str(e)}")

        return redirect('sales:pos_dashboard')
    

class SellerReportView(LoginRequiredMixin, SellerOrBakerRequiredMixin, ListView):
    """Sotuvchilar uchun faqat o'zlarining sotuvlari va kassa balansi"""
    template_name = "sales/seller_report.html"
    context_object_name = "sales"
    paginate_by = 20

    def get_queryset(self):
        # Faqat joriy tizimdagi sotuvchining sotuvlari
        queryset = Sale.objects.filter(seller=self.request.user).order_by('-created_at')
        
        # GET Filtrlarini olish
        search_query = self.request.GET.get('search', '')
        payment_filter = self.request.GET.get('payment_type', '')
        date_filter = self.request.GET.get('date_range', 'today')

        # 1. Mijoz ismi yoki telefoni bo'yicha qidiruv
        if search_query:
            queryset = queryset.filter(
                Q(customer_name__icontains=search_query) | 
                Q(customer_phone__icontains=search_query)
            )

        # 2. To'lov turi bo'yicha filtr (cash / debt)
        if payment_filter in ['cash', 'debt']:
            queryset = queryset.filter(payment_type=payment_filter)

        # 3. Sana bo'yicha filtr
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
        
        # Filtrlar holatini saqlash uchun
        context['current_search'] = self.request.GET.get('search', '')
        context['current_payment'] = self.request.GET.get('payment_type', '')
        context['current_date'] = self.request.GET.get('date_range', 'today')

        # Kassaning umumiy holatini hisoblash (Faqat filterlangan kunga oid)
        base_stats = Sale.objects.filter(seller=self.request.user)
        
        # Sana bo'yicha kassa statistikasini ham moslashtiramiz
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

class StaffExpenseCreateView(LoginRequiredMixin, CreateView):
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
    

class DebtManagementView(LoginRequiredMixin, SellerOrBakerRequiredMixin, ListView):
    """Nasiyalarni kuzatish va qisman to'lovlarni qabul qilish paneli"""
    model = Sale
    template_name = "sales/debts.html"
    context_object_name = "debts"

    def get_queryset(self):
        # Faqat to'liq yopilmagan nasiya shartnomalari/sotuvlari
        return Sale.objects.filter(
            payment_type='debt', 
            debt_status='unpaid' # Yoki balance__gt=0 mantiqiy maydoningiz bo'yicha
        ).order_by('-created_at')


def pay_debt_partially_view(request, sale_id):
    """Qarzning ma'lum bir qismini xavfsiz to'lash funksiyasi"""
    if request.method == "POST":
        amount_paid = float(request.POST.get('amount', 0))
        
        with transaction.atomic():
            # Qarz shartnomasini qulflagan holda yuklaym3z
            sale = get_object_or_404(Sale, id=sale_id, payment_type='debt')
            
            if amount_paid <= 0:
                messages.error(request, "⚠️ To'lov miqdori noldan katta bo'lishi kerak!")
                return redirect('sales:debt_dashboard')
                
            if amount_paid > float(sale.remaining_debt):
                messages.error(request, f"⚠️ Ortiqcha pul kiritildi! Maksimal qarz qoldig'i: {sale.remaining_debt:,.0f} so'm")
                return redirect('sales:debt_dashboard')

            # 1. Qarz qoldig'ini ayiramiz
            sale.remaining_debt = float(sale.remaining_debt) - amount_paid
            
            # 2. Agar qarz to'liq yopilgan bo'lsa holatni o'zgartiramiz
            if sale.remaining_debt <= 0:
                sale.debt_status = 'paid'
            sale.save()
            
            # 3. To'lovlar tarixiga qayd qilamiz
            DebtPayment.objects.create(
                sale=sale,
                collected_by=request.user,
                amount_paid=amount_paid
            )
            
            messages.success(request, f"💳 {sale.customer_name} qarzidan {amount_paid:,.0f} so'm muvaffaqiyatli qabul qilindi. Qoldiq qarz: {sale.remaining_debt:,.0f} so'm.")
            
    return redirect('sales:debt_dashboard')