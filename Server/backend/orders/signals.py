# orders/signals.py
"""
All Order and Payment post-save signals.

Key fixes applied:
  1. deduct_inventory_for_order defined ONCE only
  2. Deduction triggers on PENDING, CONFIRMED *and* COMPLETED
  3. on_commit closure captures pk (int), not instance (mutable object)
  4. Payment signal uses update_fields — never re-fires Order post_save
  5. inventory_deducted guard field prevents double-deduction
  6. Stock (menu item units) now deducted alongside InventoryItem ingredients
"""
import sys
from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

from .models import Order, Payment, Receipt
from notifications.services import NotificationService
from notifications.models import Notification
from .services import ReceiptService


# Statuses that should trigger inventory deduction
_DEDUCT_ON_STATUSES = {
    Order.OrderStatus.PENDING,
    Order.OrderStatus.CONFIRMED,
    Order.OrderStatus.COMPLETED,   # POS clerk app creates orders directly as Completed
}


# ─────────────────────────────────────────────────────────────────────────────
# INVENTORY DEDUCTION  (defined ONCE — Bug Fix #1)
# ─────────────────────────────────────────────────────────────────────────────
def _deduct_inventory(order_pk):
    """
    Called via transaction.on_commit so the order row is fully committed
    before we read it back.

    Deducts:
      • Raw ingredients  → InventoryItem  (via MenuItemIngredient)
      • Menu item units  → Stock          (if MenuItem.trackStock is True)
    """
    # Local imports avoid circular-import at module load time
    from inventory.models import InventoryItem, InventoryTransaction, MenuItemIngredient
    from menu.models import Stock, StockTransaction

    try:
        order = Order.objects.prefetch_related(
            'items__menuItem__ingredients__inventoryItem',
            'items__menuItem__stock',
        ).get(pk=order_pk)
    except Order.DoesNotExist:
        print(f"[signal] Order pk={order_pk} not found — skipping deduction.", file=sys.stderr)
        return

    # ── Bug Fix #5: never deduct twice ────────────────────────────────────
    if order.inventory_deducted:
        return

    with transaction.atomic():
        for order_item in order.items.all():
            menu_item  = order_item.menuItem
            order_qty  = Decimal(str(order_item.quantity))

            # ── 1. Raw ingredient deduction ───────────────────────────────
            ingredients = MenuItemIngredient.objects.filter(
                menuItem=menu_item
            ).select_related('inventoryItem')

            if not ingredients.exists():
                print(
                    f"[signal] No ingredients mapped for '{menu_item.name}' "
                    f"(pk={menu_item.pk}). Skipping raw deduction.",
                    file=sys.stderr,
                )
            else:
                for ingredient in ingredients:
                    qty_needed = Decimal(str(ingredient.quantityUsed)) * order_qty

                    try:
                        inv = InventoryItem.objects.select_for_update().get(
                            pk=ingredient.inventoryItem.pk
                        )
                    except InventoryItem.DoesNotExist:
                        print(
                            f"[signal] InventoryItem pk={ingredient.inventoryItem.pk} "
                            f"missing — skipping.",
                            file=sys.stderr,
                        )
                        continue

                    before        = inv.quantityInStock
                    # ── Bug Fix #4: floor at zero, never go negative ──────
                    actual_deduct = min(qty_needed, before)
                    inv.quantityInStock = max(before - qty_needed, Decimal('0'))
                    inv.save(update_fields=['quantityInStock', 'updatedAt'])

                    if actual_deduct < qty_needed:
                        print(
                            f"[signal] WARNING: '{inv.name}' insufficient — "
                            f"needed {qty_needed}, had {before}, "
                            f"deducted {actual_deduct}.",
                            file=sys.stderr,
                        )

                    InventoryTransaction.objects.create(
                        inventoryItem   = inv,
                        transactionType = InventoryTransaction.TransactionType.USAGE,
                        quantityChanged = -actual_deduct,
                        quantityBefore  = before,
                        quantityAfter   = inv.quantityInStock,
                        relatedOrder    = order,
                        note=(
                            f"Deducted for Order {order.orderNumber}: "
                            f"{order_qty}× {menu_item.name}"
                        ),
                        performedBy=order.takenBy,
                    )

            # ── 2. Menu Stock deduction (Bug Fix #6 — was missing) ────────
            if menu_item.trackStock:
                try:
                    stock = Stock.objects.select_for_update().get(menuItem=menu_item)
                except Stock.DoesNotExist:
                    print(
                        f"[signal] MenuItem '{menu_item.name}' has trackStock=True "
                        f"but no Stock row — creating at 0.",
                        file=sys.stderr,
                    )
                    stock = Stock.objects.create(menuItem=menu_item, quantity=0)

                qty_int    = int(order_item.quantity)
                before_qty = stock.quantity
                after_qty  = max(before_qty - qty_int, 0)   # floor at 0

                stock.quantity = after_qty
                stock.save(update_fields=['quantity', 'updatedAt'])

                StockTransaction.objects.create(
                    stock           = stock,
                    transactionType = StockTransaction.TransactionType.SALE,
                    quantityChanged = -(min(qty_int, before_qty)),
                    quantityBefore  = before_qty,
                    quantityAfter   = after_qty,
                    note=(
                        f"Sold in Order {order.orderNumber}: "
                        f"{qty_int}× {menu_item.name}"
                    ),
                    performedBy=order.takenBy,
                )

        # ── Bug Fix #5: mark deducted so future re-saves don't repeat ─────
        Order.objects.filter(pk=order_pk).update(inventory_deducted=True)


# ─────────────────────────────────────────────────────────────────────────────
# ORDER SIGNAL
# ─────────────────────────────────────────────────────────────────────────────
@receiver(post_save, sender=Order)
def handle_order_post_save(sender, instance, created, **kwargs):
    # ── Bug Fix #3: capture pk (int) not instance (mutable ORM object) ───
    order_pk = instance.pk

    if created:
        NotificationService.create_order_notification(
            instance,
            Notification.NotificationType.ORDER_PLACED,
        )
        # ── Bug Fix #2: include COMPLETED so POS direct-complete works ───
        if instance.status in _DEDUCT_ON_STATUSES:
            transaction.on_commit(
                lambda pk=order_pk: _deduct_inventory(pk)
            )

    else:
        if instance.status == Order.OrderStatus.COMPLETED:
            NotificationService.create_order_notification(
                instance,
                Notification.NotificationType.ORDER_COMPLETED,
            )
            # Deduct if status changed TO completed and not already done
            # e.g. kitchen app marks Preparing → Completed
            if not instance.inventory_deducted:
                transaction.on_commit(
                    lambda pk=order_pk: _deduct_inventory(pk)
                )

            # Ensure completed paid orders have an audit payment record.
            if (
                instance.paymentStatus == Order.PaymentStatus.PAID and
                not Payment.objects.filter(order=instance).exists()
            ):
                Payment.objects.create(
                    order=instance,
                    method=instance.paymentMethod or Payment.PaymentMethod.CASH,
                    amountPaid=instance.totalAmount,
                    amountChange=Decimal('0.00'),
                    verificationStatus=Payment.VerificationStatus.CONFIRMED,
                    processedBy=instance.takenBy,
                )

        elif instance.status == Order.OrderStatus.CANCELLED:
            NotificationService.create_order_notification(
                instance,
                Notification.NotificationType.ORDER_CANCELLED,
            )


# ─────────────────────────────────────────────────────────────────────────────
# PAYMENT SIGNAL
# ─────────────────────────────────────────────────────────────────────────────
@receiver(post_save, sender=Payment)
def handle_payment_creation(sender, instance, created, **kwargs):
    order = instance.order

    verified_paid = sum(
        p.amountPaid for p in order.payments.filter(
            verificationStatus=Payment.VerificationStatus.CONFIRMED
        )
    )

    if verified_paid >= order.totalAmount:
        new_status = Order.PaymentStatus.PAID
    elif verified_paid > 0:
        new_status = Order.PaymentStatus.PARTIAL
    else:
        new_status = Order.PaymentStatus.UNPAID

    # ── Bug Fix #4: update_fields bypasses Order post_save entirely ───────
    # Calling order.save() here would re-fire the Order post_save signal,
    # potentially re-running deduction and notification logic.
    if order.paymentStatus != new_status:
        Order.objects.filter(pk=order.pk).update(paymentStatus=new_status)
        order.paymentStatus = new_status   # keep in-memory copy in sync

    if created:
        NotificationService.create_payment_notification(order, instance)

    if order.paymentStatus == Order.PaymentStatus.PAID:
        if not Receipt.objects.filter(order=order).exists():
            ReceiptService.generate_receipt(order, format='Thermal')