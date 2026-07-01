from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect

class AdminRequiredMixin(UserPassesTestMixin):
    """Faqat tizim Administratori kira oladi"""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'admin'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect('users:login')
        # Kelgan sahifasiga yoki neytral Kassa oynasiga chiroyli Alert bilan qaytarish
        messages.error(self.request, "🛑 Kirish taqiqlangan! Ushbu bo'limga kirish huquqi faqat tizim Administratoriga tegishli.")
        return redirect(self.request.META.get('HTTP_REFERER', 'sales:pos_dashboard'))


class AdminOrManagerRequiredMixin(UserPassesTestMixin):
    """Faqat Admin yoki Omborchi (Manager) kira oladi"""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role in ['admin', 'manager']
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect('users:login')
        messages.warning(self.request, "⚠️ Kirish cheklangan! Bu bo'limga faqat Admin yoki Omborchi (Menejer) kira oladi.")
        return redirect(self.request.META.get('HTTP_REFERER', 'sales:pos_dashboard'))


class SalesAccessRequiredMixin(UserPassesTestMixin):
    """Sotuv va ishlab chiqarish bo'limlariga umumiy rollar nazorati"""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role in ['admin', 'manager', 'seller']

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect('users:login')
        messages.error(self.request, "🚫 Kechirasiz, sizning profilingizga ushbu sahifaga kirish huquqi berilmagan.")
        return redirect('users:login') 


class BakerOnlyRequiredMixin(UserPassesTestMixin):
    """Faqat Nonvoylar uchun"""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.role == 'baker'
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect('users:login')
        messages.warning(self.request, "👨‍🍳 Ushbu sahifa faqat Nonvoylar (ishlab chiqarish faktini kiritish) uchun mo'ljallangan!")
        return redirect(self.request.META.get('HTTP_REFERER', 'production:plan_list'))