from django.db import models
from django.conf import settings
from apps.products.models import Product
from django.db.models import Q

class ProductStock(models.Model):
    """Tayyor mahsulotlarning joriy sotuvdagi zaxirasi (Asosiy ombor)"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='stock', verbose_name="Mahsulot")
    quantity = models.PositiveIntegerField(default=0, verbose_name="Tayyor mahsulot qoldig'i (dona)")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tayyor mahsulot qoldig'i"
        verbose_name_plural = "Tayyor mahsulot qoldiqlari"

    def __str__(self):
        return f"{self.product.name}: {self.quantity} dona"


class ProductionRecord(models.Model):
    """Amalda tayyorlangan ish va ishlab chiqarish yakuni (Fakt)"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Mahsulot")
    actual_quantity = models.PositiveIntegerField(verbose_name="Amalda tayyorlangan (Sog'lom dona)")
    waste_quantity = models.PositiveIntegerField(default=0, verbose_name="Brak / Yaroqsiz (dona)")
    
    baker = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        limit_choices_to=Q(role='baker') | Q(role='admin'), 
        verbose_name="Mas'ul Nonvoy"
    )
    is_salary_calculated = models.BooleanField(default=False, verbose_name="Ish haqi hisoblandimi?")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tizimga kiritilgan vaqt")

    def calculate_baker_salary(self):
        """Ushbu partiyadan nonvoy qancha ishlab topganini hisoblash"""
        return self.actual_quantity * self.product.worker_share

    class Meta:
        verbose_name = "Ishlab chiqarish fakti"
        verbose_name_plural = "Ishlab chiqarish faktlari"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.product.name} -> {self.actual_quantity} dona"


class SellerStock(models.Model):
    """Sotuvchining vitrinasi (Alohida sotuv ombori)"""
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        limit_choices_to=Q(role='seller') | Q(role='admin'),
        verbose_name="Sotuvchi"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Mahsulot")
    quantity = models.PositiveIntegerField(default=0, verbose_name="Vitrindagi qoldiq (dona)")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Sotuvchi vitrinasi"
        verbose_name_plural = "Sotuvchilar vitrinalari"
        unique_together = ('seller', 'product')

    def __str__(self):
        return f"{self.seller.phone_number} | {self.product.name}: {self.quantity} dona"


class ProductReturn(models.Model):
    """Kun oxirida sotilmay qolgan mahsulotlar qaytimi (Vozvrat)"""
    RETURN_REASONS = [
        ('stale', 'Qatib qolgan (Sifatini yoqotgan)'),
        ('back_to_stock', 'Asosiy omborga qaytarish'),
        ('gift', 'Ehsan / Hadya'),
    ]
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="Sotuvchi")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Mahsulot")
    quantity = models.PositiveIntegerField(verbose_name="Qaytarilgan miqdor")
    reason = models.CharField(max_length=20, choices=RETURN_REASONS, verbose_name="Qaytarish sababi")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Qaytarilgan vaqt")

    class Meta:
        verbose_name = "Mahsulot qaytimi"
        verbose_name_plural = "Mahsulot qaytimlari"