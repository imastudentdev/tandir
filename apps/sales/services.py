from django.db import transaction
from apps.production.models import SellerStock
from apps.products.models import Product, ProductPrice
from .models import Sale, SaleItem
import logging

logger = logging.getLogger(__name__)

class SalesService:
    @staticmethod
    @transaction.atomic
    def create_sale(seller, customer_name, customer_phone, payment_type, cart_data):
        """
        Sotuvni rasmiylashtirish, jami kombinatsiyalangan qoldiqlarni tekshirish 
        va vitrinadan (SellerStock) avtomatik ayirish.
        """
        if not cart_data:
            raise ValueError("Savat bo'sh, sotuvni amalga oshirib bo'lmaydi!")

        # 1. Guruhlash: Savatdagi bitta mahsulotning umumiy miqdorini aniqlash
        product_total_quantities = {}
        for item in cart_data:
            p_id = int(item['product_id'])
            qty = int(item['quantity'])
            product_total_quantities[p_id] = product_total_quantities.get(p_id, 0) + qty

        # 2. Vitrina qoldiqlarini ombordan qulflagan holda tekshirish
        for p_id, total_qty in product_total_quantities.items():
            try:
                stock = SellerStock.objects.select_for_update().get(seller=seller, product_id=p_id)
                if stock.quantity < total_qty:
                    raise ValueError(
                        f"⚠️ {stock.product.name} vitrinada jami {stock.quantity} ta bor. "
                        f"Siz jami {total_qty} ta sotmoqchisiz! Qoldiq yetarli emas."
                    )
            except SellerStock.DoesNotExist:
                product_name = Product.objects.get(id=p_id).name
                raise ValueError(f"⚠️ {product_name} ushbu sotuvchining vitrinasida mavjud emas!")

        # 3. Sale obyektini yaratish
        # RegexValidator xato bermasligi uchun telefon bo'sh bo'lsa, xavfsiz default raqam beriladi
        sale = Sale.objects.create(
            seller=seller,
            customer_name=customer_name or "Chakana Xaridor",
            customer_phone=customer_phone if customer_phone else "+998990000000",
            payment_type=payment_type,
            total_amount=0  # Hisoblangach pastda yangilanadi
        )

        grand_total = 0

        # 4. Mahsulotlarni rasmiylashtirish va qoldiqdan chegirish
        for item in cart_data:
            p_id = int(item['product_id'])
            qty = int(item['quantity'])
            price_type_name = item['price_type']

            product = Product.objects.get(id=p_id)
            
            # Narxni bazadan aniq tekshirib olish
            try:
                price_obj = ProductPrice.objects.get(product=product, price_type__name=price_type_name)
                unit_price = float(price_obj.price)
            except ProductPrice.DoesNotExist:
                raise ValueError(f"[{product.name}] uchun [{price_type_name}] narxi tizimda belgilanmagan!")

            subtotal = unit_price * qty
            grand_total += subtotal

            # SaleItem yaratish
            SaleItem.objects.create(
                sale=sale,
                product=product,
                quantity=qty,
                unit_price=unit_price,
                subtotal=subtotal
            )

            # Vitrinadan ayirish
            stock = SellerStock.objects.get(seller=seller, product_id=p_id)
            stock.quantity -= qty
            stock.save()

        # Jami summani yangilash
        sale.total_amount = grand_total
        sale.save()
        
        logger.info(f"🎉 Sotuv muvaffaqiyatli yakunlandi! Chek ID: #{sale.id} | Jami: {grand_total} so'm")
        return sale