import urllib.request
import urllib.parse
import json
import time
from .models import TelegramConfig

class NotificationService:
    
    @staticmethod
    def send_telegram_message(message: str):
        """Telegram guruhga xabar yuborish (Sodda, ishonchli va tashqi kutubxonalarsiz)"""
        config = TelegramConfig.objects.filter(is_active=True).first()
        if not config or not config.bot_token or not config.chat_id:
            return  # Telegram sozlanmagan yoki faol emas bo'lsa jim to'xtaydi

        url = f"https://api.telegram.org/bot{config.bot_token}/sendMessage"
        
        # Xabarni xavfsiz jo'natish uchun ma'lumotlar
        payload = {
            "chat_id": config.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={'Content-Type': 'application/json'}
        )

        # Tranzaksiya yoki API cheklovlarida uzilishlar bo'lsa 3 marta qayta urinish (Backoff) logikasi
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    if response.status == 200:
                        return True
            except Exception as e:
                # Xatolik yuz bersa biroz kutib qayta urinadi
                time.sleep(attempt + 1)
        return False

    @staticmethod
    def check_and_alert_low_stock(ingredient, current_stock):
        """Agar omborda xomashyo belgilangan limitdan kam bo'lsa, Telegramga SOS jo'natadi"""
        config = TelegramConfig.objects.filter(is_active=True).first()
        if config and config.alert_low_stock and current_stock < ingredient.min_limit:
            msg = (
                f"🚨 *DIQQAT! OMBOARDAGI XOMASHYO KAM!* 🚨\n\n"
                f"📦 *Xomashyo:* {ingredient.name}\n"
                f"⚠️ *Joriy qoldiq:* {current_stock:.3f} {ingredient.unit}\n"
                f"📉 *Minimal limit:* {ingredient.min_limit:.3f} {ingredient.unit}\n\n"
                f"Iltimos, zaxirani tezda to'ldiring!"
            )
            NotificationService.send_telegram_message(msg)