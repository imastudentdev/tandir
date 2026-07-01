from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Q
from .models import Expense, ExpenseCategory
from apps.users.models import CustomUser

class ExpenseManageView(LoginRequiredMixin, CreateView, ListView):
    """Xarajatlarni boshqarish: Xodimlar o'z ehtiyojini kiritadi, Admin esa hammasini nazorat qiladi"""
    model = Expense
    template_name = "expenses/expense_list.html"
    fields = ['category', 'amount', 'comment', 'staff_member']
    success_url = reverse_lazy('expenses:manage_expenses')
    context_object_name = 'expenses'

    def get_queryset(self):
        user = self.request.user
        # Admin va Manager hamma xarajatni ko'radi
        if user.role in ['admin', 'manager']:
            return Expense.objects.select_related('category', 'staff_member', 'created_by').all()
        # Nonvoy va Sotuvchi faqat o'zi kiritgan yoki o'ziga tegishli xarajatlarni ko'radi
        return Expense.objects.select_related('category', 'staff_member', 'created_by').filter(
            Q(created_by=user) | Q(staff_member=user)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        context['categories'] = ExpenseCategory.objects.all()
        
        # ⚡ OPTIMIZATSIYA: sum() o'rniga bazaning o'zida tezkor hisoblash
        qs = self.get_queryset()
        context['total_expense'] = qs.aggregate(total=Sum('amount'))['total'] or 0
        
        # Formadagi staff_member ro'yxatini to'g'rilash (Faqat Admin/Manager boshqalarni tanlay oladi)
        if user.role not in ['admin', 'manager']:
            context['form'].fields['staff_member'].queryset = CustomUser.objects.filter(id=user.id)
        else:
            context['form'].fields['staff_member'].queryset = CustomUser.objects.all()
            
        return context

    def form_valid(self, form):
        user = self.request.user
        form.instance.created_by = user
        
        # Agar oddiy xodim kiritsa, majburiy ravishda uning o'ziga bog'laymiz (Xavfsizlik)
        if user.role not in ['admin', 'manager']:
            form.instance.staff_member = user
            
        messages.success(self.request, "🎉 Xarajat muvaffaqiyatli tizimga qo'shildi.")
        return super().form_valid(form)
    

class BakerExpenseCreateView(LoginRequiredMixin, CreateView):
    model = Expense
    fields = ['category', 'amount', 'staff_member', 'comment']
    template_name = 'expenses/staff_expense_form.html'
    success_url = reverse_lazy('production:plan_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ExpenseCategory.objects.all()
        from django.contrib.auth import get_user_model
        User = get_user_model()
        context['staff_members'] = User.objects.filter(is_active=True)
        context['is_baker'] = True
        return context

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, "Xarajat muvaffaqiyatli ro'yxatga olindi.")
        return super().form_valid(form)