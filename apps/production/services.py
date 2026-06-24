from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import ProductionRecord, ProductStock, SellerStock, ProductReturn
from apps.recipes.models import Recipe
from apps.inventory.services import InventoryService
from apps.inventory.models import StockMovement

class ProductionService:
    
    @staticmethod
    @transaction.atomic
    def record_production(product, actual_quantity, waste_quantity, baker):
        """Amalda non yopilganda xomashyoni FIFOdan ayirish va tayyor mahsulot omboriga qo'shish"""
        if actual_quantity <= 0:
            raise ValidationError("Tayyorlangan mahsulot miqdori 0 dan katta bo'lishi shart.")

        try:
            recipe = product.recipe
        except Recipe.DoesNotExist:
            raise ValidationError(f"[{product.name}] uchun retsept ochilmagan! Avval retsept yarating.")

        total_baked = actual_quantity + waste_quantity
        reason = f"Ishlab chiqarish: {product.name} ({actual_quantity} ta tayyor, {waste_quantity} ta brak)"

        # 1. Retsept bo'yicha masalliqlarni ombordan FIFO orqali ayiramiz
        for item in recipe.items.select_related('ingredient'):
            total_ingredient_needed = Decimal(total_baked) * item.quantity
            InventoryService.consume_stock_fifo(
                ingredient=item.ingredient,
                quantity_to_consume=total_ingredient_needed,
                reason=reason
            )

        # 2. Tayyor mahsulotlar asosiy omboriga (ProductStock) qo'shamiz
        stock, created = ProductStock.objects.get_or_create(product=product)
        stock.quantity += actual_quantity
        stock.save()

        # 3. Amaldagi fakt yozuvini yaratish
        record = ProductionRecord.objects.create(
            product=product,
            actual_quantity=actual_quantity,
            waste_quantity=waste_quantity,
            baker=baker
        )
        return record

    @staticmethod
    @transaction.atomic
    def delete_production_record(record_id):
        """Xato kiritilgan faktni o'chirish va ombor zaxiralarini hamda xomashyolarni ortga qaytarish (Revert)"""
        record = ProductionRecord.objects.get(id=record_id)
        
        if record.is_salary_calculated:
            raise ValidationError("Ushbu partiya uchun nonvoyga oylik hisoblab bo'lingan! Uni o'chirib bo'lmaydi.")
            
        # 1. Asosiy ombordan tayyor non miqdorini kamaytiramiz
        stock = ProductStock.objects.filter(product=record.product).first()
        if stock:
            if stock.quantity < record.actual_quantity:
                raise ValidationError(f"Xatolik: Ombordagi {record.product.name} soni kiritilgan miqdordan kam (Sotib bo'lingan bo'lishi mumkin)!")
            stock.quantity -= record.actual_quantity
            stock.save()

        # 2. Ishlatilgan xomashyolarni xarid sifatida omborga qayta kirim qilamiz (Tuzatish kirimi)
        total_baked = record.actual_quantity + record.waste_quantity
        recipe = record.product.recipe
        
        for item in recipe.items.select_related('ingredient'):
            total_ingredient_to_return = Decimal(total_baked) * item.quantity
            # InventoryService.add_stock funksiyasi avtomatik ravishda StockMovement (IN) yaratadi
            InventoryService.add_stock(
                ingredient=item.ingredient,
                quantity=total_ingredient_to_return,
                purchase_price=Decimal('0.00'), # Narxini 0 qilamiz, chunki bu shunchaki qaytim
                reason=f"Tuzatish: #{record.id} xato fakt o'chirilgani sabab qaytarildi"
            )

        # 3. Faktni o'chiramiz
        record.delete()

    @staticmethod
    @transaction.atomic
    def distribute_to_seller(product, seller, quantity):
        """Asosiy ombordan tayyor nonni sotuvchining vitrinasiga tarqatish"""
        if quantity <= 0:
            raise ValidationError("Tarqatiladigan miqdor 0 dan katta bo'lishi shart.")

        try:
            main_stock = ProductStock.objects.get(product=product)
        except ProductStock.DoesNotExist:
            raise ValidationError(f"Asosiy omborda [{product.name}] umuman mavjud emas.")

        if main_stock.quantity < quantity:
            raise ValidationError(
                f"Asosiy omborda yetarli [{product.name}] yo'q! "
                f"Siz so'radingiz: {quantity} ta, asosiy omborda bor: {main_stock.quantity} ta."
            )

        main_stock.quantity -= quantity
        main_stock.save()

        seller_stock, created = SellerStock.objects.get_or_create(
            seller=seller,
            product=product,
            defaults={'quantity': 0}
        )
        seller_stock.quantity += quantity
        seller_stock.save()

    @staticmethod
    @transaction.atomic
    def process_return(seller, product, quantity, reason):
        """Sotuvchi vitrinasidan qaytgan vozvratlarni qayta ishlash"""
        if quantity <= 0:
            raise ValidationError("Qaytariladigan miqdor 0 dan katta bo'lishi shart.")

        try:
            seller_stock = SellerStock.objects.get(seller=seller, product=product)
        except SellerStock.DoesNotExist:
            raise ValidationError(f"Sotuvchi vitrinasida [{product.name}] umuman mavjud emas.")

        if seller_stock.quantity < quantity:
            raise ValidationError(f"Sotuvchi vitrinasida yetarli [{product.name}] yo'q!")

        seller_stock.quantity -= quantity
        seller_stock.save()

        ProductReturn.objects.create(
            seller=seller,
            product=product,
            quantity=quantity,
            reason=reason
        )

        if reason == 'back_to_stock':
            main_stock, created = ProductStock.objects.get_or_create(product=product, defaults={'quantity': 0})
            main_stock.quantity += quantity
            main_stock.save()