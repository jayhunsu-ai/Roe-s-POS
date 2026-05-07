from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from unittest.mock import patch

from .models import (
    Supplier,
    InventoryItem,
    PurchaseOrder,
    PurchaseOrderItem,
    InventoryTransaction,
    POCounter,
    MenuItemIngredient,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_supplier(**kwargs):
    defaults = dict(name='Test Supplier', contactName='John Doe', phone='08012345678', email='supplier@test.com')
    defaults.update(kwargs)
    return Supplier.objects.create(**defaults)


def make_inventory_item(supplier=None, **kwargs):
    if supplier is None:
        supplier = make_supplier()
    defaults = dict(
        name='Rice',
        unit=InventoryItem.Unit.KG,
        quantityInStock=Decimal('10.00'),
        lowStockThreshold=Decimal('5.00'),
        costPerUnit=Decimal('2.50'),
        supplier=supplier,
    )
    defaults.update(kwargs)
    return InventoryItem.objects.create(**defaults)


_user_counter = 0

def make_staff_user(staffName='Test Manager', role=None, **kwargs):
    """Creates a Staff user matching the StaffManager.create_user() signature."""
    from accounts.models import Staff
    global _user_counter
    _user_counter += 1
    if role is None:
        role = Staff.Roles.INVENTORY_MANAGER
    email = kwargs.pop('email', f'staff{_user_counter}@test.com')
    # Handle 'username' parameter by using it as staffName if provided
    username = kwargs.pop('username', None)
    if username and not staffName:
        staffName = username
    if not staffName:
        staffName = f'staff{_user_counter}'
    user = Staff.objects.create_user(
        email=email,
        staffName=staffName,
        password='testpass123',
        role=role,
        **kwargs,
    )
    return user


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------

class SupplierModelTests(TestCase):
    def test_str(self):
        supplier = make_supplier(name='Fresh Farms')
        self.assertEqual(str(supplier), 'Fresh Farms')

    def test_default_is_active(self):
        supplier = make_supplier()
        self.assertTrue(supplier.isActive)

    def test_supplier_created_at_set(self):
        supplier = make_supplier()
        self.assertIsNotNone(supplier.createdAt)


class InventoryItemModelTests(TestCase):
    def setUp(self):
        self.supplier = make_supplier()

    def test_str(self):
        item = make_inventory_item(self.supplier, name='Rice', quantityInStock=Decimal('10.00'), unit=InventoryItem.Unit.KG)
        self.assertEqual(str(item), 'Rice (10.00 kg)')

    def test_is_low_stock_true(self):
        item = make_inventory_item(self.supplier, quantityInStock=Decimal('2.00'), lowStockThreshold=Decimal('5.00'))
        self.assertTrue(item.isLowStock)

    def test_is_low_stock_false(self):
        item = make_inventory_item(self.supplier, quantityInStock=Decimal('10.00'), lowStockThreshold=Decimal('5.00'))
        self.assertFalse(item.isLowStock)

    def test_is_low_stock_at_threshold(self):
        # exactly at threshold — still low (uses <, so equal is NOT low)
        item = make_inventory_item(self.supplier, quantityInStock=Decimal('5.00'), lowStockThreshold=Decimal('5.00'))
        self.assertFalse(item.isLowStock)

    def test_default_is_active(self):
        item = make_inventory_item(self.supplier)
        self.assertTrue(item.isActive)

    def test_unit_choices(self):
        for unit_val, _ in InventoryItem.Unit.choices:
            item = make_inventory_item(self.supplier, unit=unit_val, name=f'Item-{unit_val}')
            self.assertEqual(item.unit, unit_val)


class POCounterTests(TestCase):
    def test_po_number_auto_generated(self):
        supplier = make_supplier()
        user = make_staff_user()
        po = PurchaseOrder.objects.create(supplier=supplier, orderedBy=user)
        self.assertTrue(po.poNumber.startswith('PO-'))

    def test_po_numbers_are_sequential(self):
        supplier = make_supplier()
        user = make_staff_user()
        po1 = PurchaseOrder.objects.create(supplier=supplier, orderedBy=user)
        po2 = PurchaseOrder.objects.create(supplier=supplier, orderedBy=user)
        num1 = int(po1.poNumber.split('-')[1])
        num2 = int(po2.poNumber.split('-')[1])
        self.assertEqual(num2, num1 + 1)

    def test_po_number_zero_padded(self):
        supplier = make_supplier()
        user = make_staff_user()
        po = PurchaseOrder.objects.create(supplier=supplier, orderedBy=user)
        parts = po.poNumber.split('-')
        self.assertEqual(len(parts[1]), 4)


class PurchaseOrderItemModelTests(TestCase):
    def setUp(self):
        self.supplier = make_supplier()
        self.user = make_staff_user()
        self.po = PurchaseOrder.objects.create(supplier=self.supplier, orderedBy=self.user)
        self.item = make_inventory_item(self.supplier)

    def test_line_total_calculated_on_save(self):
        po_item = PurchaseOrderItem.objects.create(
            purchaseOrder=self.po,
            inventoryItem=self.item,
            quantityOrdered=Decimal('10.00'),
            costPerUnit=Decimal('3.00'),
            quantityReceived=Decimal('0'),
        )
        self.assertEqual(po_item.lineTotal, Decimal('30.00'))

    def test_str(self):
        po_item = PurchaseOrderItem.objects.create(
            purchaseOrder=self.po,
            inventoryItem=self.item,
            quantityOrdered=Decimal('5.00'),
            costPerUnit=Decimal('2.00'),
            quantityReceived=Decimal('0'),
        )
        self.assertIn(self.item.name, str(po_item))
        self.assertIn(self.po.poNumber, str(po_item))


class InventoryTransactionModelTests(TestCase):
    def setUp(self):
        self.supplier = make_supplier()
        self.item = make_inventory_item(self.supplier, quantityInStock=Decimal('20.00'))
        self.user = make_staff_user()

    def test_create_transaction(self):
        txn = InventoryTransaction.objects.create(
            inventoryItem=self.item,
            transactionType=InventoryTransaction.TransactionType.ADJUSTMENT,
            quantityChanged=Decimal('5.00'),
            quantityBefore=Decimal('20.00'),
            quantityAfter=Decimal('25.00'),
            performedBy=self.user,
        )
        self.assertEqual(txn.quantityAfter, Decimal('25.00'))

    def test_str(self):
        txn = InventoryTransaction.objects.create(
            inventoryItem=self.item,
            transactionType=InventoryTransaction.TransactionType.USAGE,
            quantityChanged=Decimal('-2.00'),
            quantityBefore=Decimal('20.00'),
            quantityAfter=Decimal('18.00'),
            performedBy=self.user,
        )
        self.assertIn('Usage', str(txn))
        self.assertIn(self.item.name, str(txn))


# ---------------------------------------------------------------------------
# API Tests
# ---------------------------------------------------------------------------

class BaseAPITestCase(APITestCase):
    def setUp(self):
        from accounts.models import Staff
        self.client = APIClient()
        self.user = make_staff_user(username='manager', role=Staff.Roles.INVENTORY_MANAGER)
        self.client.force_authenticate(user=self.user)
        self.supplier = make_supplier()


# --- Supplier ---

class SupplierAPITests(BaseAPITestCase):
    def test_list_suppliers(self):
        response = self.client.get(reverse('inventory:supplier-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_supplier(self):
        payload = {'name': 'New Vendor', 'email': 'vendor@test.com', 'phone': '07011112222'}
        response = self.client.post(reverse('inventory:supplier-list'), payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Vendor')

    def test_retrieve_supplier(self):
        url = reverse('inventory:supplier-detail', args=[self.supplier.supplierId])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.supplier.name)

    def test_update_supplier(self):
        url = reverse('inventory:supplier-detail', args=[self.supplier.supplierId])
        response = self.client.patch(url, {'name': 'Updated Vendor'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Vendor')

    def test_delete_supplier(self):
        url = reverse('inventory:supplier-detail', args=[self.supplier.supplierId])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_active_only_filter(self):
        make_supplier(name='Inactive Vendor', isActive=False)
        response = self.client.get(reverse('inventory:supplier-list') + '?active_only=true')
        names = [s['name'] for s in response.data]
        self.assertNotIn('Inactive Vendor', names)

    def test_inactive_suppliers_returned_when_flag_false(self):
        make_supplier(name='Inactive Vendor', isActive=False)
        response = self.client.get(reverse('inventory:supplier-list') + '?active_only=false')
        names = [s['name'] for s in response.data]
        self.assertIn('Inactive Vendor', names)

    def test_unauthenticated_list_denied(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse('inventory:supplier-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# --- InventoryItem ---

class InventoryItemAPITests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.item = make_inventory_item(self.supplier)

    def test_list_items(self):
        response = self.client.get(reverse('inventory:inventoryitem-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_item(self):
        payload = {
            'name': 'Oil',
            'unit': 'L',
            'quantityInStock': '20.00',
            'lowStockThreshold': '5.00',
            'costPerUnit': '1.50',
            'supplierId': str(self.supplier.supplierId),
        }
        response = self.client.post(reverse('inventory:inventoryitem-list'), payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Oil')

    def test_low_stock_returns_flag(self):
        low_item = make_inventory_item(self.supplier, name='Low Rice', quantityInStock=Decimal('1.00'), lowStockThreshold=Decimal('5.00'))
        url = reverse('inventory:inventoryitem-detail', args=[low_item.inventoryItemId])
        response = self.client.get(url)
        self.assertTrue(response.data['isLowStock'])

    def test_low_stock_action(self):
        make_inventory_item(self.supplier, name='Low Item', quantityInStock=Decimal('1.00'), lowStockThreshold=Decimal('5.00'))
        response = self.client.get(reverse('inventory:inventoryitem-low-stock'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [i['name'] for i in response.data]
        self.assertIn('Low Item', names)

    def test_out_of_stock_action(self):
        make_inventory_item(self.supplier, name='Empty Item', quantityInStock=Decimal('0.00'))
        response = self.client.get(reverse('inventory:inventoryitem-out-of-stock'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [i['name'] for i in response.data]
        self.assertIn('Empty Item', names)

    def test_update_item(self):
        url = reverse('inventory:inventoryitem-detail', args=[self.item.inventoryItemId])
        response = self.client.patch(url, {'name': 'Basmati Rice'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Basmati Rice')

    def test_delete_item(self):
        url = reverse('inventory:inventoryitem-detail', args=[self.item.inventoryItemId])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


# --- PurchaseOrder ---

class PurchaseOrderAPITests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.item = make_inventory_item(self.supplier)

    def _po_payload(self):
        return {
            'supplierId': str(self.supplier.supplierId),
            'note': 'Restock order',
            'items': [
                {
                    'inventoryItemId': str(self.item.inventoryItemId),
                    'quantityOrdered': '10.00',
                    'quantityReceived': '0',
                    'costPerUnit': '3.00',
                }
            ],
        }

    def test_create_purchase_order(self):
        response = self.client.post(reverse('inventory:purchaseorder-list'), self._po_payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['poNumber'].startswith('PO-'))
        self.assertEqual(Decimal(response.data['totalCost']), Decimal('30.00'))

    def test_list_purchase_orders(self):
        self.client.post(reverse('inventory:purchaseorder-list'), self._po_payload(), format='json')
        response = self.client.get(reverse('inventory:purchaseorder-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_cannot_edit_items_on_non_draft_po(self):
        create_resp = self.client.post(reverse('inventory:purchaseorder-list'), self._po_payload(), format='json')
        po_id = create_resp.data['purchaseOrderId']

        # Receive the PO first to move it out of DRAFT
        self.client.post(reverse('inventory:purchaseorder-receive', args=[po_id]))

        update_payload = {
            'items': [
                {
                    'inventoryItemId': str(self.item.inventoryItemId),
                    'quantityOrdered': '20.00',
                    'quantityReceived': '0',
                    'costPerUnit': '3.00',
                }
            ]
        }
        update_resp = self.client.patch(
            reverse('inventory:purchaseorder-detail', args=[po_id]),
            update_payload,
            format='json'
        )
        self.assertEqual(update_resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_receive_purchase_order_updates_stock(self):
        before_qty = self.item.quantityInStock
        create_resp = self.client.post(reverse('inventory:purchaseorder-list'), self._po_payload(), format='json')
        po_id = create_resp.data['purchaseOrderId']

        receive_resp = self.client.post(reverse('inventory:purchaseorder-receive', args=[po_id]))
        self.assertEqual(receive_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(receive_resp.data['status'], 'Received')

        self.item.refresh_from_db()
        self.assertEqual(self.item.quantityInStock, before_qty + Decimal('10.00'))

    def test_receive_creates_inventory_transaction(self):
        create_resp = self.client.post(reverse('inventory:purchaseorder-list'), self._po_payload(), format='json')
        po_id = create_resp.data['purchaseOrderId']
        self.client.post(reverse('inventory:purchaseorder-receive', args=[po_id]))

        txn = InventoryTransaction.objects.filter(
            transactionType=InventoryTransaction.TransactionType.PURCHASE,
            inventoryItem=self.item,
        ).first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.quantityChanged, Decimal('10.00'))

    def test_receive_already_received_returns_400(self):
        create_resp = self.client.post(reverse('inventory:purchaseorder-list'), self._po_payload(), format='json')
        po_id = create_resp.data['purchaseOrderId']
        self.client.post(reverse('inventory:purchaseorder-receive', args=[po_id]))
        # attempt second receive
        resp2 = self.client.post(reverse('inventory:purchaseorder-receive', args=[po_id]))
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_receive_uses_quantity_received_if_set(self):
        """If quantityReceived is specified on line items, that value is used instead of quantityOrdered."""
        before_qty = self.item.quantityInStock

        # Create a PO item with partial receipt
        payload = self._po_payload()
        payload['items'][0]['quantityReceived'] = '6.00'

        create_resp = self.client.post(reverse('inventory:purchaseorder-list'), payload, format='json')
        po_id = create_resp.data['purchaseOrderId']

        # Manually set quantityReceived on the PO item (simulating partial delivery)
        po = PurchaseOrder.objects.get(pk=po_id)
        po_item = po.items.first()
        po_item.quantityReceived = Decimal('6.00')
        po_item.save()

        self.client.post(reverse('inventory:purchaseorder-receive', args=[po_id]))

        self.item.refresh_from_db()
        self.assertEqual(self.item.quantityInStock, before_qty + Decimal('6.00'))


# --- InventoryTransaction ---

class InventoryTransactionAPITests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.item = make_inventory_item(self.supplier)
        self.txn = InventoryTransaction.objects.create(
            inventoryItem=self.item,
            transactionType=InventoryTransaction.TransactionType.ADJUSTMENT,
            quantityChanged=Decimal('5.00'),
            quantityBefore=Decimal('10.00'),
            quantityAfter=Decimal('15.00'),
            performedBy=self.user,
        )

    def test_list_transactions(self):
        response = self.client.get(reverse('inventory:inventorytransaction-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_retrieve_transaction(self):
        url = reverse('inventory:inventorytransaction-detail', args=[self.txn.transactionId])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['transactionType'], 'Adjustment')

    def test_transactions_are_read_only(self):
        """Inventory transactions should not allow POST/PATCH/DELETE."""
        response = self.client.post(reverse('inventory:inventorytransaction-list'), {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_filter_by_transaction_type(self):
        wastage_txn = InventoryTransaction.objects.create(
            inventoryItem=self.item,
            transactionType=InventoryTransaction.TransactionType.WASTAGE,
            quantityChanged=Decimal('-1.00'),
            quantityBefore=Decimal('15.00'),
            quantityAfter=Decimal('14.00'),
            performedBy=self.user,
        )
        url = reverse('inventory:inventorytransaction-list') + '?transactionType=Wastage'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only return Wastage transactions
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['transactionId'], str(wastage_txn.transactionId))
        self.assertEqual(response.data[0]['transactionType'], 'Wastage')
