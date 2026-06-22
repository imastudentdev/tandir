from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.recipes.models import Ingredient

class IngredientBatch(models.Model):
    """Omborga kelib tushgan xomashyo partiyalari (FIFO uchun juda muhim)"""
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='batches', verbose_name="Ingredient")
    initial_quantity = models.DecimalField(max_digits=12, decimal_places=3, verbose_name="Keltirilgan miqdor")
    remaining_quantity = models.DecimalField(
        max_digits=12, 
        decimal_places=3, 
        validators=[MinValueValidator(Decimal('0.000'))],
        verbose_name="Qolgan miqdor"
    )
    purchase_price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Sotib olish narxi (1 birlik uchun)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Kirim vaqti")

    class Meta:
        verbose_name = "Xomashyo partiyasi"
        verbose_name_plural = "Xomashyo partiyalari"
        ordering = ['created_at']

    def __str__(self):
        return f"{self.ingredient.name} | Qoldiq: {self.remaining_quantity} | Narxi: {self.purchase_price} so'm"


class StockMovement(models.Model):
    """Ombordagi barcha harakatlar tarixi (Audit log va hisobotlar uchun)"""
    MOVEMENT_TYPES = [
        ('IN', 'Kirim (Satib olindi)'),
        ('OUT', 'Chiqim (Ishlab chiqarishga)'),
        ('WASTE', 'Yaroqsiz (Brak / Isrof)'),
    ]

    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='movements', verbose_name="Ingredient")
    movement_type = models.CharField(max_length=10, choices=MOVEMENT_TYPES, verbose_name="Harakat turi")
    quantity = models.DecimalField(max_digits=12, decimal_places=3, verbose_name="Miqdor")
    batch = models.ForeignKey(IngredientBatch, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Tegishli partiya")
    reason = models.CharField(max_length=255, blank=True, null=True, verbose_name="Sabab / Izoh")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Harakat vaqti")

    class Meta:
        verbose_name = "Ombor harakati"
        verbose_name_plural = "Ombor harakatlari"

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.ingredient.name}: {self.quantity}"
    