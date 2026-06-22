from django.contrib import admin
from .models import IngredientBatch, StockMovement

@admin.register(IngredientBatch)
class IngredientBatchAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'initial_quantity', 'remaining_quantity', 'purchase_price', 'created_at')
    list_filter = ('ingredient', 'created_at')
    search_fields = ('ingredient__name',)

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('ingredient', 'movement_type', 'quantity', 'reason', 'created_at')
    list_filter = ('movement_type', 'ingredient', 'created_at')
    search_fields = ('ingredient__name', 'reason')