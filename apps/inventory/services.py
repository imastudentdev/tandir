from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Sum
from decimal import Decimal
from .models import IngredientBatch, StockMovement
from apps.recipes.models import Ingredient

class InventoryService:
    
    @staticmethod
    def get_total_stock(ingredient: Ingredient) -> Decimal:
        """Ingredientning ombardagi joriy umumiy qoldig'ini qaytaradi"""
        result = IngredientBatch.objects.filter(
            ingredient=ingredient, 
            remaining_quantity__gt=0
        ).aggregate(total=Sum('remaining_quantity'))
        return result['total'] or Decimal('0.000')

    @staticmethod
    @transaction.atomic
    def add_stock(ingredient: Ingredient, quantity: Decimal, purchase_price: Decimal, reason="Yangi xarid"):
        """Omborga yangi xomashyo partiyasini qo'shish (Kirim qilish)"""
        if quantity <= 0:
            raise ValidationError("Kirim qilinadigan miqdor 0 dan katta bo'lishi shart.")
            
        # 1. Yangi partiya (Batch) yaratamiz
        batch = IngredientBatch.objects.create(
            ingredient=ingredient,
            initial_quantity=quantity,
            remaining_quantity=quantity,
            purchase_price=purchase_price
        )
        
        # 2. Harakatlar tarixiga kirim sifatida yozamiz
        StockMovement.objects.create(
            ingredient=ingredient,
            movement_type='IN',
            quantity=quantity,
            batch=batch,
            reason=reason
        )
        return batch

    @staticmethod
    @transaction.atomic
    def consume_stock_fifo(ingredient: Ingredient, quantity_to_consume: Decimal, reason: str):
        """FIFO logikasi asosida ombordan xomashyo ayirish (Chiqim qilish)"""
        if quantity_to_consume <= 0:
            return

        total_available = InventoryService.get_total_stock(ingredient)
        
        # Omborda yetarli xomashyo borligini tekshiramiz (Minusga kirishni qat'iy bloklash)
        if total_available < quantity_to_consume:
            raise ValidationError(
                f"Omborda [{ingredient.name}] yetarli emas! "
                f"Sizga {quantity_to_consume} {ingredient.unit} kerak, ammo joriy qoldiq {total_available} {ingredient.unit}."
            )

        remaining_to_deduct = quantity_to_consume

        # Eng eski partiyadan (FIFO: created_at bo'yicha) boshlab olamiz
        active_batches = IngredientBatch.objects.filter(
            ingredient=ingredient, 
            remaining_quantity__gt=0
        ).order_by('created_at')

        for batch in active_batches:
            if remaining_to_deduct <= 0:
                break

            if batch.remaining_quantity >= remaining_to_deduct:
                # Ushbu partiyaning o'zidan yetarli bo'lsa
                batch.remaining_quantity -= remaining_to_deduct
                
                StockMovement.objects.create(
                    ingredient=ingredient,
                    movement_type='OUT',
                    quantity=remaining_to_deduct,
                    batch=batch,
                    reason=reason
                )
                batch.save()
                remaining_to_deduct = Decimal('0.000')
            else:
                # Partiyadagi hamma qoldiqni tugatib, keyingisiga o'tamiz
                deducted_from_this_batch = batch.remaining_quantity
                remaining_to_deduct -= deducted_from_this_batch
                
                batch.remaining_quantity = Decimal('0.000')
                
                StockMovement.objects.create(
                    ingredient=ingredient,
                    movement_type='OUT',
                    quantity=deducted_from_this_batch,
                    batch=batch,
                    reason=reason
                )
                batch.save()