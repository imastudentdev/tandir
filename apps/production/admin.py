from django.contrib import admin
from django.contrib import messages
from .models import ProductStock, ProductionPlan, ProductionRecord, SellerStock
from .services import ProductionService

@admin.register(ProductStock)
class ProductStockAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'updated_at')
    search_fields = ('product__name',)

@admin.register(ProductionPlan)
class ProductionPlanAdmin(admin.ModelAdmin):
    list_display = ('date', 'product', 'planned_quantity', 'status', 'created_at')
    list_filter = ('status', 'date')
    search_fields = ('product__name',)

@admin.register(ProductionRecord)
class ProductionRecordAdmin(admin.ModelAdmin):
    list_display = ('product', 'actual_quantity', 'waste_quantity', 'baker', 'created_at')
    list_filter = ('baker', 'created_at')
    search_fields = ('product__name', 'baker__full_name')

@admin.register(SellerStock)
class SellerStockAdmin(admin.ModelAdmin):
    list_display = ('seller', 'product', 'quantity', 'updated_at')
    list_filter = ('seller', 'product')
    search_fields = ('seller__full_name', 'product__name')
    
    def save_model(self, request, obj, form, change):
        """
        Admin paneldan yangi taqsimot qo'shilganda yoki o'zgartirilganda 
        ProductionService ichidagi tayyor mantiqni ishga tushiradi.
        """
        try:
            ProductionService.distribute_to_seller(
                product=obj.product,
                seller=obj.seller,
                quantity=obj.quantity
            )
            self.message_user(
                request, 
                f"{obj.quantity} ta [{obj.product.name}] muvaffaqiyatli [{obj.seller.full_name or obj.seller.phone_number}] vitrinasiga o'tkazildi (Asosiy ombordan chegirildi).", 
                level=messages.SUCCESS
            )
        except Exception as e:
            self.message_user(request, f"Xatolik yuz berdi: {str(e)}", level=messages.ERROR)
            
    def response_add(self, request, obj, post_url_continue=None):
        return super().response_add(request, obj, post_url_continue)
