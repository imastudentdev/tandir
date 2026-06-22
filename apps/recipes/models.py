from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from apps.products.models import Product

class Ingredient(models.Model):
    """Omborda turadigan xomashyolar (masalan: Un, Tuz, Shakar, Yog')"""
    UNIT_CHOICES = [
        ('kg', 'Kilogramm'),
        ('litr', 'Litr'),
        ('dona', 'Dona'),
        ('gramm', 'Gramm'),
    ]

    name = models.CharField(max_length=150, unique=True, verbose_name="Ingredient nomi")
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='kg', verbose_name="O'lchov birligi")
    
    # Kelajakda Telegram alert yuborish uchun minimum miqdor cheklovi
    min_limit = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        validators=[MinValueValidator(Decimal('0.000'))],
        default=Decimal('10.000'),
        verbose_name="Minimal qoldiq limiti"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_unit_display()})"

    class Meta:
        verbose_name = "Ingredient (Xomashyo)"
        verbose_name_plural = "Ingredientlar (Xomashyolar)"


class Recipe(models.Model):
    """Retseptning asosiy qismi. Har bitta mahsulotning faqat bitta faol retsepti bo'ladi."""
    product = models.OneToOneField(
        Product, 
        on_delete=models.CASCADE, 
        related_name='recipe', 
        verbose_name="Tayyor mahsulot"
    )
    description = models.TextField(blank=True, null=True, verbose_name="Tayyorlanish usuli (Tavsif)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.product.name} uchun retsept"

    class Meta:
        verbose_name = "Retsept"
        verbose_name_plural = "Retseptlar"


class RecipeItem(models.Model):
    """Retsept tarkibidagi aniq ingredientlar va ularning sarf-harajati (1 dona mahsulot uchun)"""
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='items', verbose_name="Retsept")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT, verbose_name="Ingredient")
    
    # 1 dona tayyor mahsulotga ketadigan miqdor (masalan: 0.350 kg un)
    quantity = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        validators=[MinValueValidator(Decimal('0.0001'))],
        verbose_name="Ketadigan miqdor (1 dona uchun)"
    )

    class Meta:
        verbose_name = "Retsept tarkibiy qismi"
        verbose_name_plural = "Retsept tarkiblari"
        # Bitta retsept ichida bitta ingredient faqat bir marta kelishi kerak
        unique_together = ('recipe', 'ingredient')

    def __str__(self):
        return f"{self.ingredient.name} - {self.quantity} {self.ingredient.unit}"