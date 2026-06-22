from django.db import transaction
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import ProductionPlan, ProductionRecord, ProductStock, SellerStock, ProductReturn
from apps.recipes.models import Recipe
from apps.inventory.services import InventoryService
from apps.users.models import CustomUser

class ProductionService:
    
    @staticmethod
    @transaction.atomic
    def record_production(product, actual_quantity, waste_quantity, baker, plan=None):
        """Nonvoyxonada amalda non yopilganda xomashyoni FIFOdan ayirish va tayyor omborga qo'shish"""
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
            plan=plan,
            product=product,
            actual_quantity=actual_quantity,
            waste_quantity=waste_quantity,
            baker=baker
        )

        if plan:
            plan.status = 'completed'
            plan.save()

        return record

    @staticmethod
    @transaction.atomic
    def distribute_to_seller(product, seller, quantity):
        """Asosiy ombordan (ProductStock) tayyor nonni sotuvchining vitrinasiga (SellerStock) tarqatish"""
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

        # 1. Asosiy ombordan ayiramiz
        main_stock.quantity -= quantity
        main_stock.save()

        # 2. Sotuvchi vitrinasiga qo'shamiz
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
            raise ValidationError(
                f"Sotuvchi vitrinasida yetarli [{product.name}] yo'q! "
                f"Mavjud: {seller_stock.quantity} ta, siz qaytarmoqchisiz: {quantity} ta."
            )

        # 1. Vitrinadan ayiramiz
        seller_stock.quantity -= quantity
        seller_stock.save()

        # 2. Qaytarilgan mahsulot yozuvini yaratamiz
        ProductReturn.objects.create(
            seller=seller,
            product=product,
            quantity=quantity,
            reason=reason
        )

        # 3. Agar sababi 'Asosiy omborga qaytarish' bo'lsa, asosiy omborga qayta qo'shamiz
        if reason == 'back_to_stock':
            main_stock, created = ProductStock.objects.get_or_create(product=product, defaults={'quantity': 0})
            main_stock.quantity += quantity
            main_stock.save()