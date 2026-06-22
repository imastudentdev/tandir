from django.db import models

class TelegramConfig(models.Model):
    """Telegram xabarnomalarini sozlash modeli (Yagona sozlama - Singleton pattern)"""
    bot_token = models.CharField(max_length=255, verbose_name="Telegram Bot Token")
    chat_id = models.CharField(max_length=100, verbose_name="Guruh yoki Kanal ID (Chat ID)")
    
    # Alert turlarini boshqarish
    alert_low_stock = models.BooleanField(default=True, verbose_name="Xomashyo kam qolganda ogohlantirish?")
    alert_new_debt = models.BooleanField(default=True, verbose_name="Yangi qarz urilganda ogohlantirish?")
    alert_daily_report = models.BooleanField(default=True, verbose_name="Kunlik moliyaviy hisobotni Telegramga jo'natish?")
    
    is_active = models.BooleanField(default=True, verbose_name="Telegram xizmati faolmi?")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Telegram Sozlamasi"
        verbose_name_plural = "Telegram Sozlamalari"

    def __str__(self):
        return f"Telegram Sozlamalari (Aktivlik: {self.is_active})"

    def save(self, *args, **kwargs):
        # Bazada har doim faqat bitta sozlama bo'lishini ta'minlaymiz
        if not self.pk and TelegramConfig.objects.exists():
            # Agar sozlama allaqachon mavjud bo'lsa, yangisini yaratishga ruxsat bermaymiz
            return
        super().save(*args, **kwargs)