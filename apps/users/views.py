from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.urls import reverse_lazy

class UserLoginForm(AuthenticationForm):
    """Telefon raqami va parol orqali tizimga kirish formasi"""
    username = forms.CharField(
        label="Telefon raqami",
        widget=forms.TextInput(attrs={
            'placeholder': '+998901234567',
            'class': 'w-full px-4 py-3 border rounded-xl outline-none focus:ring-2 focus:ring-blue-500'
        })
    )
    password = forms.CharField(
        label="Parol",
        widget=forms.PasswordInput(attrs={
            'placeholder': '••••••••',
            'class': 'w-full px-4 py-3 border rounded-xl outline-none focus:ring-2 focus:ring-blue-500'
        })
    )

class UserLoginView(LoginView):
    template_name = 'users/login.html'
    authentication_form = UserLoginForm

    def get_success_url(self):
        """Foydalanuvchini roliga qarab aniq va xavfsiz sahifaga yo'naltirish"""
        user = self.request.user
        
        if hasattr(user, 'role'):
            if user.role == 'seller':
                return reverse_lazy('sales:pos_dashboard')
            
            elif user.role == 'baker':
                # Nonvoylar uchun maxsus ishlab chiqarish rejalari sahifasi
                return reverse_lazy('production:plan_list')
            
            elif user.role in ['admin', 'manager']:
                # Admin va menejerlar uchun umumiy tahliliy dashboard
                return reverse_lazy('reports:dashboard')
        
        # Agar rol topilmasa, standart holat
        return reverse_lazy('sales:pos_dashboard')

class UserLogoutView(LogoutView):
    next_page = 'users:login'