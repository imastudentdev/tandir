from django.contrib import admin
from .models import Ingredient, Recipe, RecipeItem

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'min_limit', 'created_at')
    search_fields = ('name',)
    list_filter = ('unit',)

class RecipeItemInline(admin.TabularInline):
    model = RecipeItem
    extra = 2  # Avtomatik 2 ta bo'sh qator chiqarish
    min_num = 1 # Kamida 1 ta ingredient bo'lishi shart

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('product', 'created_at', 'updated_at')
    search_fields = ('product__name',)
    inlines = [RecipeItemInline]