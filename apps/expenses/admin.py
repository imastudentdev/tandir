from django.contrib import admin
from .models import ExpenseCategory, Expense

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('category', 'amount', 'staff_member', 'created_by', 'date')
    list_filter = ('category', 'date', 'created_by')
    search_fields = ('comment', 'staff_member__full_name', 'created_by__full_name')
    date_hierarchy = 'date'