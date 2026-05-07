"""
Tests for orders/signals.py — specifically the deduct_inventory_for_order path.

Two test classes are used deliberately:

  DeductInventoryUnitTests (TestCase)
      Calls deduct_inventory_for_order() directly.
      Fast; runs inside a rolled-back transaction so the DB is clean after each test.
      Covers all the logic branches without touching the signal machinery.

  DeductInventorySignalTests (TransactionTestCase)
      Saves an Order with status=COMPLETED so the real post_save signal fires
      and transaction.on_commit() actually executes.
      Slower (DB is truncated, not rolled back, after each test) but proves
      the wiring from signal → on_commit → deduct_inventory_for_order works end-to-end.
      Keep the number of tests here small — only the happy path needs proving at
      this level; edge cases are cheaper to cover in the unit class above.
"""

from decimal import Decimal

from django.test import TestCase, TransactionTestCase
from unittest.mock import patch

from accounts.models import Staff
from inventory.models import InventoryItem, InventoryTransaction, MenuItemIngredient, Supplier
from menu.models import MenuItem
from orders.models import Order, OrderItem
from orders.signals import deduct_inventory_for_order


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def make_staff(email='clerk@test.com', name='Clerk', role=None):
    if role is None:
        role = Staff.Roles.CLERK
    return Staff.objects.create_user(email=email, staffName=name, password='123456', role=role)


def make_supplier():
    return Supplier.objects.create(name='Test Supplier', email='s@test.com')


def make_inventory_item(supplier, name='Rice', quantity='20.00', unit=InventoryItem.Unit.KG):
    return InventoryItem.objects.create(
        name=name,
        unit=unit,
        quantityInStock=Decimal(quantity),
        lowStockThreshold=Decimal('5.00'),
        costPerUnit=Decimal('2.00'),
        supplier=supplier,
    )


def make_menu_item(name='Jollof Rice', price='1500.00'):
    return MenuItem.objects.create(name=name, price=Decimal(price))


def make_order(clerk, total='1500.00'):
    return Order.objects.create(takenBy=clerk, totalAmount=Decimal(total))


def make_order_item(order, menu_item, quantity=1):
    return OrderItem.objects.create(
        order=order,
        menuItem=menu_item,
        quantity=quantity,
        unitPrice=menu_item.price,
        lineTotal=menu_item.price * quantity,
    )


def link_ingredient(menu_item, inventory_item, quantity_used='0.200'):
    """Link a menu item to an inventory item with quantityUsed per serving."""
    return MenuItemIngredient.objects.create(
        menuItem=menu_item,
        inventoryItem=inventory_item,
        quantityUsed=Decimal(quantity_used),
    )


# ---------------------------------------------------------------------------
# Unit tests — call deduct_inventory_for_order() directly
# ---------------------------------------------------------------------------

class DeductInventoryUnitTests(TestCase):
    """
    Fast unit tests for the deduct_inventory_for_order function.
    Notifications are patched out so these tests don't depend on that service.
    """

    def setUp(self):
        self.clerk = make_staff()
        self.supplier = make_supplier()
        self.rice = make_inventory_item(self.supplier, name='Rice', quantity='20.00')
        self.oil = make_inventory_item(self.supplier, name='Oil', quantity='10.00', unit=InventoryItem.Unit.LITRES)
        self.menu_item = make_menu_item('Jollof Rice')
        # 200g rice + 50ml oil per serving
        link_ingredient(self.menu_item, self.rice, '0.200')
        link_ingredient(self.menu_item, self.oil, '0.050')
        self.order = make_order(self.clerk)
        self.order_item = make_order_item(self.order, self.menu_item, quantity=2)

    def test_stock_reduced_by_correct_amount(self):
        """2 servings × 200g rice = 400g (0.400 kg) deducted."""
        deduct_inventory_for_order(self.order)

        self.rice.refresh_from_db()
        self.assertEqual(self.rice.quantityInStock, Decimal('20.00') - Decimal('0.400'))

    def test_all_ingredients_deducted(self):
        """Both rice and oil should be reduced."""
        deduct_inventory_for_order(self.order)

        self.rice.refresh_from_db()
        self.oil.refresh_from_db()
        self.assertEqual(self.rice.quantityInStock, Decimal('19.600'))
        self.assertEqual(self.oil.quantityInStock, Decimal('10.00') - Decimal('0.100'))

    def test_inventory_transaction_created_per_ingredient(self):
        """One USAGE transaction should be created for each ingredient."""
        deduct_inventory_for_order(self.order)

        txns = InventoryTransaction.objects.filter(
            relatedOrder=self.order,
            transactionType=InventoryTransaction.TransactionType.USAGE,
        )
        self.assertEqual(txns.count(), 2)

    def test_transaction_quantity_changed_is_negative(self):
        """quantityChanged must be negative (stock removed)."""
        deduct_inventory_for_order(self.order)

        for txn in InventoryTransaction.objects.filter(relatedOrder=self.order):
            self.assertLess(txn.quantityChanged, 0)

    def test_transaction_before_and_after_are_correct(self):
        """quantityBefore and quantityAfter should reflect the actual stock values."""
        deduct_inventory_for_order(self.order)

        rice_txn = InventoryTransaction.objects.get(
            relatedOrder=self.order,
            inventoryItem=self.rice,
        )
        self.assertEqual(rice_txn.quantityBefore, Decimal('20.00'))
        self.assertEqual(rice_txn.quantityAfter, Decimal('19.600'))
        self.assertEqual(rice_txn.quantityChanged, Decimal('-0.400'))

    def test_transaction_performed_by_is_order_taker(self):
        """performedBy on the transaction should be the clerk who took the order."""
        deduct_inventory_for_order(self.order)

        for txn in InventoryTransaction.objects.filter(relatedOrder=self.order):
            self.assertEqual(txn.performedBy, self.clerk)

    def test_transaction_note_contains_order_number_and_menu_item(self):
        """The audit note should reference the order number and menu item name."""
        deduct_inventory_for_order(self.order)

        for txn in InventoryTransaction.objects.filter(relatedOrder=self.order):
            self.assertIn(self.order.orderNumber, txn.note)
            self.assertIn(self.menu_item.name, txn.note)

    def test_multiple_order_items_all_deducted(self):
        """An order with two different menu items deducts ingredients for both."""
        pasta = make_menu_item('Pasta', price='1200.00')
        flour = make_inventory_item(self.supplier, name='Flour', quantity='5.00')
        link_ingredient(pasta, flour, '0.100')
        make_order_item(self.order, pasta, quantity=3)

        deduct_inventory_for_order(self.order)

        flour.refresh_from_db()
        # 3 servings × 100g = 300g deducted
        self.assertEqual(flour.quantityInStock, Decimal('5.00') - Decimal('0.300'))

    def test_menu_item_with_no_ingredients_does_nothing(self):
        """If a menu item has no linked ingredients, no transactions are created and no error raised."""
        no_ingredient_item = make_menu_item('Plain Water', price='100.00')
        order = make_order(self.clerk, total='100.00')
        make_order_item(order, no_ingredient_item, quantity=1)

        # Should not raise
        deduct_inventory_for_order(order)

        self.assertEqual(
            InventoryTransaction.objects.filter(relatedOrder=order).count(), 0
        )

    def test_stock_can_go_below_zero(self):
        """
        The function does not enforce a stock floor — it deducts whatever the
        recipe demands. A separate low-stock alert handles this case.
        Verify the behaviour is intentional and consistent.
        """
        self.rice.quantityInStock = Decimal('0.10')
        self.rice.save()

        deduct_inventory_for_order(self.order)  # needs 0.400 kg, only 0.10 available

        self.rice.refresh_from_db()
        self.assertEqual(self.rice.quantityInStock, Decimal('0.10') - Decimal('0.400'))

    def test_order_with_no_items_does_nothing(self):
        """An empty order should create no transactions and raise no errors."""
        empty_order = make_order(self.clerk)

        deduct_inventory_for_order(empty_order)

        self.assertEqual(
            InventoryTransaction.objects.filter(relatedOrder=empty_order).count(), 0
        )

    def test_deduction_is_atomic(self):
        """
        If deduction fails mid-way (e.g. DB error on second ingredient),
        the whole operation should roll back — no partial stock changes.
        """
        # Force an error after the first ingredient save by making the second
        # inventory item lookup raise an exception.
        call_count = {'n': 0}
        original_save = InventoryItem.save

        def patched_save(self_item, *args, **kwargs):
            call_count['n'] += 1
            if call_count['n'] == 2:
                raise Exception("Simulated DB failure on second ingredient")
            original_save(self_item, *args, **kwargs)

        with patch.object(InventoryItem, 'save', patched_save):
            with self.assertRaises(Exception, msg="Simulated DB failure on second ingredient"):
                deduct_inventory_for_order(self.order)

        # Both items should be unchanged because the transaction rolled back
        self.rice.refresh_from_db()
        self.oil.refresh_from_db()
        self.assertEqual(self.rice.quantityInStock, Decimal('20.00'))
        self.assertEqual(self.oil.quantityInStock, Decimal('10.00'))


# ---------------------------------------------------------------------------
# Integration test — verify the signal wiring fires via on_commit
# ---------------------------------------------------------------------------

class DeductInventorySignalTests(TransactionTestCase):
    """
    Uses TransactionTestCase so that transaction.on_commit() callbacks actually
    execute. Django's standard TestCase wraps each test in a transaction that
    is never committed, so on_commit never fires there.

    These tests are slower because the DB is fully truncated after each test
    rather than rolled back. Keep coverage here minimal — just enough to prove
    the signal → on_commit → deduct_inventory_for_order chain works.
    """

    def setUp(self):
        self.clerk = make_staff(email='clerk-signal@test.com')
        self.supplier = make_supplier()
        self.rice = make_inventory_item(self.supplier, name='Rice', quantity='20.00')
        self.menu_item = make_menu_item('Jollof Rice')
        link_ingredient(self.menu_item, self.rice, '0.200')

    @patch('orders.signals.NotificationService.create_order_notification')
    def test_completing_order_deducts_stock_via_signal(self, mock_notify):
        """
        Setting order.status = COMPLETED and saving should trigger the signal,
        which schedules deduct_inventory_for_order via on_commit.
        Stock should be reduced after the save commits.
        """
        order = make_order(self.clerk)
        make_order_item(order, self.menu_item, quantity=1)

        order.status = Order.OrderStatus.COMPLETED
        order.save()

        self.rice.refresh_from_db()
        # 1 serving × 200g = 200g deducted from 20.00 kg
        self.assertEqual(self.rice.quantityInStock, Decimal('20.00') - Decimal('0.200'))

    @patch('orders.signals.NotificationService.create_order_notification')
    def test_non_completed_status_does_not_deduct_stock(self, mock_notify):
        """
        Saving an order with status other than COMPLETED should not touch stock.
        """
        order = make_order(self.clerk)
        make_order_item(order, self.menu_item, quantity=1)

        for non_completing_status in [
            Order.OrderStatus.CONFIRMED,
            Order.OrderStatus.PREPARING,
            Order.OrderStatus.READY,
            Order.OrderStatus.SERVED,
            Order.OrderStatus.CANCELLED,
        ]:
            order.status = non_completing_status
            order.save()

        self.rice.refresh_from_db()
        self.assertEqual(self.rice.quantityInStock, Decimal('20.00'))

    @patch('orders.signals.NotificationService.create_order_notification')
    def test_completing_order_creates_usage_transaction_via_signal(self, mock_notify):
        """
        The InventoryTransaction audit record should be created when an order
        completes through the normal signal path.
        """
        order = make_order(self.clerk)
        make_order_item(order, self.menu_item, quantity=2)

        order.status = Order.OrderStatus.COMPLETED
        order.save()

        txn = InventoryTransaction.objects.filter(
            relatedOrder=order,
            transactionType=InventoryTransaction.TransactionType.USAGE,
        ).first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.quantityChanged, Decimal('-0.400'))
