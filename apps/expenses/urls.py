from django.urls import path
from .views import ExpenseManageView, BakerExpenseCreateView

app_name = 'expenses'

urlpatterns = [
    path('manage/', ExpenseManageView.as_view(), name='manage_expenses'),
    path('baker-add/', BakerExpenseCreateView.as_view(), name='baker_add_expense'),
]