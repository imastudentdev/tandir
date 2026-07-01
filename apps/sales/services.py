from django.db import transaction
from django.utils import timezone
from .models import Sale, SaleItem
from apps.products.models import Product, ProductPrice
from apps.production.models import SellerStock, ProductStock

class SalesService:
    @staticmethod
    @transaction.atomic
    def create_sale(seller, customer_name, customer_phone, payment_type, cart_data):
        if not cart_data:
            raise ValueError("Savat bo'sh, sotuvni amalga oshirib bo'lmaydi!")

        is_direct = seller.role in ['admin', 'manager']
        product_total_quantities = {}
        for item in cart_data:
            p_id = int(item['product_id'])
            qty = int(item['quantity'])
            product_total_quantities[p_id] = product_total_quantities.get(p_id, 0) + qty

        # Qoldiqni tekshirish (select_for_update orqali lock qilish)
        for p_id, total_qty in product_total_quantities.items():
            if is_direct:
                try:
                    stock = ProductStock.objects.select_for_update().get(product_id=p_id)
                    if stock.quantity < total_qty:
                        raise ValueError(f"⚠️ {stock.product.name} Asosiy Omborda jami {stock.quantity} ta bor. Qoldiq yetarli emas!")
                except ProductStock.DoesNotExist:
                    raise ValueError("⚠️ Mahsulot asosiy omborda mavjud emas!")
            else:
                try:
                    stock = SellerStock.objects.select_for_update().get(seller=seller, product_id=p_id)
                    if stock.quantity < total_qty:
                        raise ValueError(f"⚠️ {stock.product.name} vitrinangizda jami {stock.quantity} ta bor. Qoldiq yetarli emas!")
                except SellerStock.DoesNotExist:
                    raise ValueError("⚠️ Ushbu mahsulot vitrinangizda mavjud emas!")

        # Savdo ob'ektini yaratish
        sale = Sale.objects.create(
            seller=seller,
            customer_name=customer_name or "Chakana Xaridor",
            customer_phone=customer_phone if customer_phone else "+998990000000",
            payment_type=payment_type,
            total_amount=0
        )

        grand_total = 0
        for item in cart_data:
            p_id = int(item['product_id'])
            qty = int(item['quantity'])
            price_type_name = item['price_type']

            product = Product.objects.get(id=p_id)
            try:
                price_obj = ProductPrice.objects.get(product=product, price_type__name=price_type_name)
                unit_price = price_obj.price
            except ProductPrice.DoesNotExist:
                raise ValueError(f"[{product.name}] uchun [{price_type_name}] narxi belgilanmagan!")

            subtotal = unit_price * qty
            grand_total += subtotal

            SaleItem.objects.create(
                sale=sale, product=product, quantity=qty, unit_price=unit_price, subtotal=subtotal
            )

            # Ombordan yoki Vitrinadan ayirish
            if is_direct:
                stock = ProductStock.objects.get(product_id=p_id)
            else:
                stock = SellerStock.objects.get(seller=seller, product_id=p_id)
            
            stock.quantity -= qty
            stock.save()

        sale.total_amount = grand_total
        sale.save()
        return sale