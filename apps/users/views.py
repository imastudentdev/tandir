from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import AuthenticationForm
from django import forms

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

class UserLogoutView(LogoutView):
    next_page = 'users:login'