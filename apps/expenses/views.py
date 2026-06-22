from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.users.mixins import AdminRequiredMixin
from .models import Expense, ExpenseCategory

class ExpenseManageView(LoginRequiredMixin, AdminRequiredMixin, CreateView, ListView):
    """Xarajatlarni boshqarish, kiritish va tahlil qilish (Faqat Admin va Rahbarlar uchun)"""
    model = Expense
    template_name = "expenses/expense_list.html"
    fields = ['category', 'amount', 'comment', 'staff_member']
    success_url = reverse_lazy('expenses:manage_expenses')
    context_object_name = 'expenses'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ExpenseCategory.objects.all()
        
        total_expense = sum(exp.amount for exp in Expense.objects.all())
        context['total_expense'] = total_expense
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Xarajat muvaffaqiyatli tizimga qo'shildi.")
        
        return super().form_valid(form)