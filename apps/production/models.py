from django.db import models
from django.conf import settings
from apps.products.models import Product
from django.db.models import Q

class ProductStock(models.Model):
    """Tayyor mahsulotlarning joriy sotuvdagi zaxirasi (ombori)"""
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='stock', verbose_name="Mahsulot")
    quantity = models.PositiveIntegerField(default=0, verbose_name="Tayyor mahsulot qoldig'i (dona)")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tayyor mahsulot qoldig'i"
        verbose_name_plural = "Tayyor mahsulot qoldiqlari"

    def __str__(self):
        return f"{self.product.name}: {self.quantity} dona"


class ProductionPlan(models.Model):
    """Kunlik ishlab chiqarish rejasi (Plan)"""
    STATUS_CHOICES = [
        ('pending', 'Kutilmoqda'),
        ('completed', 'Bajarildi'),
        ('cancelled', 'Bekor qilindi'),
    ]
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Mahsulot")
    planned_quantity = models.PositiveIntegerField(verbose_name="Rejalashtirilgan miqdor (dona)")
    date = models.DateField(verbose_name="Reja sanasi")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending', verbose_name="Holati")
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def progress_percentage(self):
        """Reja bo'yicha tayyorlangan mahsulotlar foizini xavfsiz hisoblash"""
        if self.planned_quantity and self.planned_quantity > 0:
            total_actual = self.productionrecord_set.aggregate(
                total=models.Sum('actual_quantity')
            )['total'] or 0
            
            percent = (total_actual / self.planned_quantity) * 100
            return min(int(percent), 100)
        return 0

    class Meta:
        verbose_name = "Ishlab chiqarish rejasi"
        verbose_name_plural = "Ishlab chiqarish rejalari"

    def __str__(self):
        return f"{self.date} | {self.product.name} - {self.planned_quantity} dona"


class ProductionRecord(models.Model):
    """Amalda bajarilgan ish va ishlab chiqarish yakuni (Fakt)"""
    plan = models.ForeignKey(ProductionPlan, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Asoslangan reja")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Mahsulot")
    
    actual_quantity = models.PositiveIntegerField(verbose_name="Amalda tayyorlangan (Sog'lom dona)")
    waste_quantity = models.PositiveIntegerField(default=0, verbose_name="Brak / Yaroqsiz (dona)")
    
    # TUZATILDI: Mas'ul Nonvoy sifatida ham nonvoylar, ham barcha adminlar (rahbarlar) tanlanishi mumkin. is_staff cheklovi olib tashlandi.
    baker = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        limit_choices_to=Q(role='baker') | Q(role='admin'), 
        verbose_name="Mas'ul Nonvoy"
    )
    is_salary_calculated = models.BooleanField(
        default=False, 
        verbose_name="Ish haqi hisoblandimi?"
    )

    def calculate_baker_salary(self):
        """Ushbu partiyadan nonvoy qancha ishlab topganini hisoblash"""
        return self.actual_quantity * self.product.worker_share

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Tizimga kiritilgan vaqt")

    class Meta:
        verbose_name = "Ishlab chiqarish fakti"
        verbose_name_plural = "Ishlab chiqarish faktlari"

    def __str__(self):
        return f"{self.product.name} -> {self.actual_quantity} dona ({self.baker.full_name or self.baker.phone_number})"
    

class SellerStock(models.Model):
    """Sotuvchining vitrinasi (Alohida sotuv ombori)"""
    # TUZATILDI: Sotuvchi vitrinasi sifatida ham sotuvchilar, ham hamma huquqqa ega adminlar biriktirilishi mumkin.
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
        return f"{self.seller.full_name or self.seller.phone_number} | {self.product.name}: {self.quantity} dona"


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