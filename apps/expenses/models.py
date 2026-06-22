from django.db import models
from django.conf import settings

class ExpenseCategory(models.Model):
    """Xarajat toifalari: Kommunal, Ijara, Transport, Ishchilar ovqati va h.k."""
    name = models.CharField(max_length=100, unique=True, verbose_name="Toifa nomi")
    description = models.TextField(blank=True, null=True, verbose_name="Tavsif")

    class Meta:
        verbose_name = "Xarajat toifasi"
        verbose_name_plural = "Xarajat toifalari"

    def __str__(self):
        return self.name


class Expense(models.Model):
    """Kundalik chiqimlar va xarajatlar balansi"""
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name='expenses', verbose_name="Kategoriya")
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Xarajat summasi")
    comment = models.TextField(verbose_name="Izoh / Nima maqsadda ishlatildi")
    
    staff_member = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='staff_expenses',
        verbose_name="Xodim (Agar tegishli bo'lsa)"
    )

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name="Mas'ul xodim")
    date = models.DateField(auto_now_add=True, verbose_name="Xarajat sanasi")

    class Meta:
        verbose_name = "Xarajat"
        verbose_name_plural = "Xarajatlar"
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.category.name} - {self.amount:,.0f} so'm ({self.date})"