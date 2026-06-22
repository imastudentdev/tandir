from django.contrib import admin
from .models import Product, PriceType, ProductPrice

@admin.register(PriceType)
class PriceTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at')
    search_fields = ('name',)

class ProductPriceInline(admin.TabularInline):
    model = ProductPrice
    extra = 1 # Standart holatda bitta bo'sh qator ko'rsatish
    min_num = 1 # Kamida bitta narx bo'lishi shart

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'sku')
    inlines = [ProductPriceInline]