from django.views.generic import ListView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.forms import inlineformset_factory
from django.shortcuts import redirect, render
from apps.users.mixins import AdminRequiredMixin, SellerOrBakerRequiredMixin
from .models import Ingredient, Recipe, RecipeItem

class IngredientListView(SellerOrBakerRequiredMixin, ListView):
    """Xomashyolar ro'yxati va ularning minimal limitlari"""
    model = Ingredient
    template_name = 'recipes/ingredient_list.html'
    context_object_name = 'ingredients'

class IngredientCreateView(AdminRequiredMixin, CreateView):
    """Yangi xomashyo (Ingredient) qo'shish"""
    model = Ingredient
    fields = ['name', 'unit', 'min_limit']
    template_name = 'recipes/ingredient_form.html'
    success_url = reverse_lazy('recipes:ingredient_list')

    def form_valid(self, form):
        messages.success(self.request, f"[{form.instance.name}] muvaffaqiyatli qo'shildi.")
        return super().form_valid(form)

class RecipeListView(SellerOrBakerRequiredMixin, ListView):
    """Barcha retseptlar ro'yxati"""
    model = Recipe
    template_name = 'recipes/recipe_list.html'
    context_object_name = 'recipes'
    
    def get_queryset(self):
        return Recipe.objects.all().select_related('product').prefetch_related('items__ingredient')

RecipeItemFormSet = inlineformset_factory(
    Recipe, RecipeItem, 
    fields=['ingredient', 'quantity'], 
    extra=3, 
    can_delete=True
)

def manage_recipe_view(request, pk=None):
    """Retseptni uning tarkibidagi ingredientlar (RecipeItems) bilan dinamik boshqarish"""
    if not request.user.is_authenticated or request.user.role != 'admin':
        messages.error(request, "Sizda ushbu operatsiyani bajarish huquqi yo'q!")
        return redirect('recipes:recipe_list')

    recipe = None
    if pk:
        recipe = Recipe.objects.get(pk=pk)

    if request.method == "POST":
        if recipe:
            formset = RecipeItemFormSet(request.POST, instance=recipe)
        else:
            product_id = request.POST.get('product')
            recipe = Recipe.objects.create(product_id=product_id, description=request.POST.get('description'))
            formset = RecipeItemFormSet(request.POST, instance=recipe)

        if formset.is_valid():
            formset.save()
            messages.success(request, "Retsept muvaffaqiyatli saqlandi.")
            return redirect('recipes:recipe_list')
    else:
        formset = RecipeItemFormSet(instance=recipe) if recipe else RecipeItemFormSet()

    return render(request, 'recipes/recipe_form.html', {
        'formset': formset,
        'recipe': recipe,
    })