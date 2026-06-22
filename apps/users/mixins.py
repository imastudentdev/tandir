from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect

class AdminRequiredMixin(UserPassesTestMixin):
    """Faqat Admin (Rahbar) kira oladi"""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'admin'
    
    def handle_no_permission(self):
        messages.error(self.request, "Bu sahifaga kirish uchun sizda yetarli huquq yo'q!")
        return redirect('sales:pos_dashboard')

class SellerOrBakerRequiredMixin(UserPassesTestMixin):
    """Sotuvchi, Nonvoy yoki Admin kira oladi (Masalan: POS uchun)"""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role in ['admin', 'seller', 'baker']
    
    def handle_no_permission(self):
        messages.error(self.request, "Tizimga tizim xodimi sifatida kiring!")
        return redirect('users:login')