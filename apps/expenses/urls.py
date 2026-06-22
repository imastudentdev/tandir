from django.urls import path
from .views import ExpenseManageView

app_name = 'expenses'

urlpatterns = [
    path('manage/', ExpenseManageView.as_view(), name='manage_expenses'),
]