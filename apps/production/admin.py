from django.contrib import admin
from django.contrib import messages
from .models import ProductStock, ProductionRecord, SellerStock, ProductReturn
from .services import ProductionService

@admin.register(ProductStock)
class ProductStockAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'updated_at')
    search_fields = ('product__name',)
    list_filter = ('updated_at',)


@admin.register(ProductionRecord)
class ProductionRecordAdmin(admin.ModelAdmin):
    list_display = ('product', 'actual_quantity', 'waste_quantity', 'baker', 'is_salary_calculated', 'created_at')
    list_filter = ('baker', 'is_salary_calculated', 'created_at')
    search_fields = ('product__name', 'baker__username', 'baker__first_name', 'baker__last_name')
    date_hierarchy = 'created_at'


@admin.register(SellerStock)
class SellerStockAdmin(admin.ModelAdmin):
    list_display = ('seller', 'product', 'quantity', 'updated_at')
    list_filter = ('seller', 'product')
    search_fields = ('seller__phone_number', 'seller__username', 'product__name')
    
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
            # Agarda userda full_name bo'lsa uni, yo'q bo'lsa phone_number'ni ko'rsatish
            seller_identifier = getattr(obj.seller, 'full_name', None) or obj.seller.phone_number or obj.seller.username
            
            self.message_user(
                request, 
                f"{obj.quantity} ta [{obj.product.name}] muvaffaqiyatli [{seller_identifier}] vitrinasiga o'tkazildi (Asosied ombordan chegirildi).", 
                level=messages.SUCCESS
            )
        except Exception as e:
            self.message_user(request, f"Xatolik yuz berdi: {str(e)}", level=messages.ERROR)
            
    def response_add(self, request, obj, post_url_continue=None):
        return super().response_add(request, obj, post_url_continue)


@admin.register(ProductReturn)
class ProductReturnAdmin(admin.ModelAdmin):
    list_display = ('seller', 'product', 'quantity', 'reason', 'created_at')
    list_filter = ('reason', 'created_at', 'seller', 'product')
    search_fields = ('seller__phone_number', 'seller__username', 'product__name')
    date_hierarchy = 'created_at'
