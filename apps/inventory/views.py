from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth.mixins import LoginRequiredMixin
# Faqat sizda mavjud bo'lgan miksinlar import qilindi
from apps.users.mixins import AdminOrManagerRequiredMixin
from .models import IngredientBatch, StockMovement
from .services import InventoryService
from apps.recipes.models import Ingredient

class InventoryDashboardView(LoginRequiredMixin, ListView):
    """Omborda turgan barcha xomashyo qoldiqlari ro'yxati (Admin, Manager va Nonvoylarga ruxsat bor)"""
    model = IngredientBatch
    template_name = 'inventory/dashboard.html'
    context_object_name = 'batches'

    def dispatch(self, request, *args, **kwargs):
        # Mantiqiy cheklov: Faqat boshqaruvchilar va nonvoylar ko'ra oladi (Sotuvchilar kira olmaydi)
        if request.user.is_authenticated and request.user.role in ['admin', 'manager', 'baker']:
            return super().dispatch(request, *args, **kwargs)
        messages.error(request, "⚠️ Xomashyo omborini ko'rish uchun sizda ruxsat yo'q!")
        return redirect('production:plan_list')

    def get_queryset(self):
        return IngredientBatch.objects.filter(remaining_quantity__gt=0).select_related('ingredient')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        ingredients = Ingredient.objects.all()
        stock_summary = []
        for ing in ingredients:
            stock_summary.append({
                'ingredient': ing,
                'total_stock': InventoryService.get_total_stock(ing)
            })
        context['stock_summary'] = stock_summary
        return context


class AddStockView(AdminOrManagerRequiredMixin, CreateView):
    """Omborga yangi xomashyo kirim qilish (Faqat Admin yoki Manager uchun)"""
    model = IngredientBatch
    fields = ['ingredient', 'initial_quantity', 'purchase_price']
    template_name = 'inventory/add_stock.html'
    success_url = reverse_lazy('inventory:dashboard')

    def post(self, request, *args, **kwargs):
        ingredient_id = request.POST.get('ingredient')
        quantity = request.POST.get('initial_quantity')
        price = request.POST.get('purchase_price')
        
        try:
            ingredient = Ingredient.objects.get(id=ingredient_id)
            InventoryService.add_stock(
                ingredient=ingredient,
                quantity=quantity,
                purchase_price=price,
                reason="Omborchi/Boshqaruvchi tomonidan qo'shildi"
            )
            messages.success(request, f"🚚 {quantity} {ingredient.unit} [{ingredient.name}] omborga muvaffaqiyatli kirim qilindi.")
        except Exception as e:
            messages.error(request, f"❌ Xatolik yuz berdi: {str(e)}")
            
        return redirect('inventory:dashboard')