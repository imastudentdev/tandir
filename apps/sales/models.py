import urllib.parse
from django.db import models
from django.conf import settings
from django.core.validators import RegexValidator
from apps.products.models import Product

class Sale(models.Model):
    PAYMENT_CHOICES = [
        ('cash', 'Naqd pul'), 
        ('debt', 'Qarzga (Nasiya)')
    ]
    
    DEBT_STATUS_CHOICES = [
        ('paid', 'Yopildi'),
        ('unpaid', 'To\'lanmoqda / Faol')
    ]
    
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="Sotuvchi / Xodim")
    customer_name = models.CharField(max_length=150, verbose_name="Mijoz ismi")
    phone_regex = RegexValidator(regex=r'^\+998\d{9}$', message="Format: +998YYXXXXXXX")
    customer_phone = models.CharField(validators=[phone_regex], max_length=13, verbose_name="Mijoz telefoni")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Umumiy hisob")
    payment_type = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='cash', verbose_name="To'lov turi")
    
    remaining_debt = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Qolgan qarz summasi")
    debt_status = models.CharField(max_length=10, choices=DEBT_STATUS_CHOICES, default='paid', verbose_name="Qarz holati")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Sotilgan vaqt")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Sotuv"
        verbose_name_plural = "Sotuvlar"

    def save(self, *args, **kwargs):
        if not self.pk and self.payment_type == 'debt':
            self.remaining_debt = self.total_amount
            self.debt_status = 'unpaid'
        super().save(*args, **kwargs)

    @property
    def telegram_link(self):
        clean_phone = self.customer_phone.replace("+", "").replace(" ", "").strip()
        status = "To'landi ✅" if self.payment_type != 'debt' else f"Nasiya ⚠️ (Qoldiq: {self.remaining_debt:,.0f} so'm)"
        
        bakery_name = "Nonvoyxona ERP"
        if hasattr(self.seller, 'full_name') and self.seller.full_name:
            bakery_name = f"{self.seller.full_name} nonvoyxonasi"

        message = (
            f"🍞 *{bakery_name}*\n"
            f"👤 Xaridor: {self.customer_name}\n"
            f"💰 Jami hisob: {self.total_amount:,.0f} so'm\n"
            f"💳 To'lov: {self.get_payment_type_display()}\n"
            f"📊 Holat: {status}\n\n"
            f"Xaridingiz uchun rahmat!"
        )
        return f"https://t.me/{clean_phone}?text={urllib.parse.quote(message)}"

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(verbose_name="Soni")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Sotilgan narxi")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Oraliq summa")


class DebtPayment(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='debt_payments', verbose_name="Qaysi qarz uchun")
    collected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="Pulni yig'gan xodim")
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="To'langan miqdor")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="To'lov vaqti")

    class Meta:
        verbose_name = "Qarz To'lovi"
        verbose_name_plural = "Qarz To'lovlari"