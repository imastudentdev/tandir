from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.forms import inlineformset_factory
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
# Faqat sizda mavjud bo'lgan miksinlar import qilindi
from apps.users.mixins import AdminOrManagerRequiredMixin
from .models import Ingredient, Recipe, RecipeItem
from apps.products.models import Product

class IngredientListView(LoginRequiredMixin, ListView):
    """Xomashyolar ro'yxati (Admin, Manager va Nonvoylar ko'ra oladi, Sotuvchiga ruxsat yo'q)"""
    model = Ingredient
    template_name = 'recipes/ingredient_list.html'
    context_object_name = 'ingredients'

    def dispatch(self, request, *args, **kwargs):
        # Mantiqiy cheklov: Faqat admin, manager va nonvoy (baker) ko'ra oladi
        if request.user.is_authenticated and request.user.role in ['admin', 'manager', 'baker']:
            return super().dispatch(request, *args, **kwargs)
        messages.error(request, "⚠️ Xomashyo qoldiqlarini ko'rish uchun huquqingiz yetarli emas!")
        return redirect('production:plan_list')


class IngredientCreateView(AdminOrManagerRequiredMixin, CreateView):
    """Yangi xomashyo (Ingredient) qo'shish (Faqat Admin yoki Manager)"""
    model = Ingredient
    fields = ['name', 'unit', 'min_limit']
    template_name = 'recipes/ingredient_form.html'
    success_url = reverse_lazy('recipes:ingredient_list')

    def form_valid(self, form):
        messages.success(self.request, f"🎉 [{form.instance.name}] xomashyolarga muvaffaqiyatli qo'shildi.")
        return super().form_valid(form)


class RecipeListView(LoginRequiredMixin, ListView):
    """Barcha retseptlar ro'yxati (Admin, Manager va Nonvoylar ko'ra oladi)"""
    model = Recipe
    template_name = 'recipes/recipe_list.html'
    context_object_name = 'recipes'
    
    def dispatch(self, request, *args, **kwargs):
        # Mantiqiy cheklov: Sotuvchilar retseptlarni ko'ra olmaydi
        if request.user.is_authenticated and request.user.role in ['admin', 'manager', 'baker']:
            return super().dispatch(request, *args, **kwargs)
        messages.error(request, "⚠️ Retseptlarni ko'rish faqat ishlab chiqarish xodimlariga ruxsat etilgan!")
        return redirect('production:plan_list')

    def get_queryset(self):
        return Recipe.objects.all().select_related('product').prefetch_related('items__ingredient')


# Dinamik ingredientlar formseti
RecipeItemFormSet = inlineformset_factory(
    Recipe, RecipeItem, 
    fields=['ingredient', 'quantity'], 
    extra=3, 
    can_delete=True
)


def manage_recipe_view(request, pk=None):
    """Retseptni dinamik boshqarish/tahrirlash (Faqat Admin yoki Manager)"""
    # To'g'ri va xavfsiz kirish nazorati
    if not request.user.is_authenticated or request.user.role not in ['admin', 'manager']:
        messages.error(request, "⚠️ Retseptlarni o'zgartirish huquqi faqat boshqaruvchilarga berilgan!")
        return redirect('recipes:recipe_list')

    recipe = None
    if pk:
        recipe = get_object_or_404(Recipe, pk=pk)

    if request.method == "POST":
        if recipe:
            formset = RecipeItemFormSet(request.POST, instance=recipe)
        else:
            product_id = request.POST.get('product')
            # Mahsulot mavjudligini tekshirish
            product = get_object_or_404(Product, id=product_id)
            recipe = Recipe.objects.create(product=product, description=request.POST.get('description'))
            formset = RecipeItemFormSet(request.POST, instance=recipe)

        if formset.is_valid():
            formset.save()
            messages.success(request, "💾 Retsept va uning tarkibi muvaffaqiyatli saqlandi.")
            return redirect('recipes:recipe_list')
        else:
            messages.error(request, "❌ Ma'lumotlarni saqlashda xatolik yuz berdi. Shaklni tekshiring.")
    else:
        formset = RecipeItemFormSet(instance=recipe) if recipe else RecipeItemFormSet()

    return render(request, 'recipes/recipe_form.html', {
        'formset': formset,
        'recipe': recipe,
        'products': Product.objects.filter(recipe__isnull=True) if not recipe else None # Yangi retsept uchun retseptsiz mahsulotlar
    })