from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class PriceType(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Narx turi nomi")
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Narx turi"
        verbose_name_plural = "Narx turlari"


class Product(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Mahsulot nomi")
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Artikul / SKU")
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Rasm")
    is_active = models.BooleanField(default=True, verbose_name="Aktivmi?")
    worker_share = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=0.00, 
        verbose_name="1 ta non uchun nonvoy xaqi (so'm)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"


class ProductPrice(models.Model):
    """Mahsulotlarning har bir narx turi bo'yicha qiymati (Dinamik narxlar)"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='prices', verbose_name="Mahsulot")
    price_type = models.ForeignKey(PriceType, on_delete=models.CASCADE, verbose_name="Narx turi")
    price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        verbose_name="Narxi (so'm)"
    )

    class Meta:
        verbose_name = "Mahsulot narxi"
        verbose_name_plural = "Mahsulot narxlari"
        unique_together = ('product', 'price_type')

    def __str__(self):
        return f"{self.product.name} - {self.price_type.name}: {self.price} so'm"