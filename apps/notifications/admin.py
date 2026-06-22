from django.contrib import admin
from .models import TelegramConfig

@admin.register(TelegramConfig)
class TelegramConfigAdmin(admin.ModelAdmin):
    list_display = ('id', 'is_active', 'alert_low_stock', 'alert_new_debt', 'alert_daily_report', 'updated_at')
    
    def has_add_permission(self, request):
        # Singleton pattern: Agar sozlama bitta bo'lsa, qayta qo'shish tugmasini yashiradi
        return not TelegramConfig.objects.exists()