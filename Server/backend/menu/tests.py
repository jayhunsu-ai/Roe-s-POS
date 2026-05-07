from django.conf import settings
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from accounts.models import Staff
from inventory.models import InventoryItem, MenuItemIngredient
from menu.models import Category, MenuItem, MenuItemAddon, Stock, StockTransaction
from menu.serializers import (
    CategorySerializer,
    MenuItemListSerializer,
    MenuItemSerializer,
    StockSerializer,
    StockTransactionSerializer,
)


def make_staff(email, name, role):
    return Staff.objects.create_user(
        email=email,
        staffName=name,
        role=role,
        password='123456',
    )


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


class MenuModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Drinks')
        self.item = MenuItem.objects.create(
            category=self.category,
            name='Water',
            price='100.00',
            trackStock=True,
        )

    def test_category_string_representation(self):
        self.assertEqual(str(self.category), 'Drinks')

    def test_menu_item_string_representation_uses_currency_symbol(self):
        expected_label = getattr(settings, 'CURRENCY_SYMBOL', '₦')
        self.assertEqual(str(self.item), f'Water - {expected_label}100.00')

    def test_is_in_stock_true_when_stock_not_tracked(self):
        no_track_item = MenuItem.objects.create(
            category=self.category,
            name='Juice',
            price='150.00',
            trackStock=False,
        )
        self.assertTrue(no_track_item.isInStock)

    def test_is_in_stock_false_when_tracked_and_no_stock_record(self):
        self.assertFalse(self.item.isInStock)

    def test_is_in_stock_respects_stock_quantity(self):
        stock = Stock.objects.create(
            menuItem=self.item,
            quantity=0,
            lowStockThreshold=5,
            unit='bottles',
        )
        self.assertFalse(self.item.isInStock)
        stock.quantity = 4
        stock.save(update_fields=['quantity'])
        self.assertTrue(self.item.isInStock)

    def test_stock_string_and_low_stock_property(self):
        stock = Stock.objects.create(
            menuItem=self.item,
            quantity=2,
            lowStockThreshold=5,
            unit='bottles',
        )
        self.assertEqual(str(stock), 'Water - 2 bottles')
        self.assertTrue(stock.isLowStock)

    def test_menu_item_addon_string_representation(self):
        addon = MenuItemAddon.objects.create(
            menuItem=self.item,
            name='Extra Ice',
            extraPrice='50.00',
        )
        expected_label = getattr(settings, 'CURRENCY_SYMBOL', '₦')
        self.assertEqual(str(addon), f'Extra Ice (+{expected_label}50.00) for Water')


class MenuSerializerTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name='Meals')
        self.item_available = MenuItem.objects.create(
            category=self.category,
            name='Burger',
            price='2500.00',
            isAvailable=True,
            trackStock=True,
        )
        self.item_unavailable = MenuItem.objects.create(
            category=self.category,
            name='Fries',
            price='1200.00',
            isAvailable=False,
            trackStock=False,
        )
        self.stock = Stock.objects.create(
            menuItem=self.item_available,
            quantity=3,
            lowStockThreshold=4,
            unit='plates',
        )
        self.inventory_item = InventoryItem.objects.create(name='Bun', unit='units', quantityInStock='20.00')
        MenuItemIngredient.objects.create(
            menuItem=self.item_available,
            inventoryItem=self.inventory_item,
            quantityUsed='1.000',
        )
        self.staff = make_staff('admin@pos.com', 'Admin User', Staff.Roles.ADMIN)
        self.transaction = StockTransaction.objects.create(
            stock=self.stock,
            transactionType=StockTransaction.TransactionType.ADJUSTMENT,
            quantityChanged=-1,
            quantityBefore=4,
            quantityAfter=3,
            note='Correction',
            performedBy=self.staff,
        )

    def test_category_serializer_counts_only_available_items(self):
        data = CategorySerializer(self.category).data
        self.assertEqual(data['menu_items_count'], 1)

    def test_menu_item_list_serializer_includes_stock_fields(self):
        data = MenuItemListSerializer(self.item_available).data
        self.assertEqual(data['category_name'], 'Meals')
        self.assertTrue(data['is_in_stock'])
        self.assertEqual(data['stock_quantity'], 3)

    def test_menu_item_list_serializer_stock_quantity_none_without_tracking(self):
        data = MenuItemListSerializer(self.item_unavailable).data
        self.assertIsNone(data['stock_quantity'])

    def test_menu_item_serializer_includes_stock_info_and_ingredients_count(self):
        data = MenuItemSerializer(self.item_available).data
        self.assertEqual(data['ingredients_count'], 1)
        self.assertIsNotNone(data['stock_info'])
        self.assertEqual(data['stock_info']['quantity'], 3)

    def test_stock_serializer_exposes_is_low_stock(self):
        data = StockSerializer(self.stock).data
        self.assertTrue(data['is_low_stock'])
        self.assertEqual(data['menu_item_name'], 'Burger')

    def test_stock_transaction_serializer_exposes_performed_by_name(self):
        data = StockTransactionSerializer(self.transaction).data
        self.assertEqual(data['performed_by_name'], 'Admin User')
        self.assertEqual(data['menu_item_name'], 'Burger')


class MenuApiTests(APITestCase):
    def setUp(self):
        self.admin = make_staff('admin@test.com', 'Admin', Staff.Roles.ADMIN)
        self.clerk = make_staff('clerk@test.com', 'Clerk', Staff.Roles.CLERK)
        self.inventory_manager = make_staff(
            'inventory@test.com',
            'Inventory Manager',
            Staff.Roles.INVENTORY_MANAGER,
        )

        self.admin_client = auth_client(self.admin)
        self.clerk_client = auth_client(self.clerk)
        self.inventory_client = auth_client(self.inventory_manager)

        self.active_category = Category.objects.create(name='Active Cat', isActive=True)
        self.inactive_category = Category.objects.create(name='Inactive Cat', isActive=False)

        self.available_item = MenuItem.objects.create(
            category=self.active_category,
            name='Pepper Soup',
            price='3000.00',
            isAvailable=True,
            trackStock=False,
        )
        self.unavailable_item = MenuItem.objects.create(
            category=self.active_category,
            name='Malt',
            price='900.00',
            isAvailable=False,
            trackStock=False,
        )
        self.tracked_out_of_stock_item = MenuItem.objects.create(
            category=self.active_category,
            name='Fish',
            price='4500.00',
            isAvailable=True,
            trackStock=True,
        )
        self.tracked_in_stock_item = MenuItem.objects.create(
            category=self.active_category,
            name='Chicken',
            price='3500.00',
            isAvailable=True,
            trackStock=True,
        )
        self.stock_out = Stock.objects.create(
            menuItem=self.tracked_out_of_stock_item,
            quantity=0,
            lowStockThreshold=2,
            unit='plates',
        )
        self.stock_in = Stock.objects.create(
            menuItem=self.tracked_in_stock_item,
            quantity=2,
            lowStockThreshold=5,
            unit='plates',
        )

        self.categories_url = reverse('menu:category-list')
        self.items_url = reverse('menu:menuitem-list')
        self.stock_url = reverse('menu:stock-list')
        self.stock_transactions_url = reverse('menu:stocktransaction-list')

    def test_category_list_requires_authentication(self):
        response = self.client.get(self.categories_url)
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_category_list_defaults_to_active_only(self):
        response = self.clerk_client.get(self.categories_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [row['name'] for row in response.data]
        self.assertIn('Active Cat', names)
        self.assertNotIn('Inactive Cat', names)

    def test_category_list_can_include_inactive_categories(self):
        response = self.clerk_client.get(self.categories_url, {'active_only': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [row['name'] for row in response.data]
        self.assertIn('Active Cat', names)
        self.assertIn('Inactive Cat', names)

    def test_only_admin_can_create_category(self):
        payload = {'name': 'Soups', 'description': 'Hot soups'}
        clerk_response = self.clerk_client.post(self.categories_url, payload)
        self.assertEqual(clerk_response.status_code, status.HTTP_403_FORBIDDEN)

        admin_response = self.admin_client.post(self.categories_url, payload)
        self.assertEqual(admin_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Category.objects.filter(name='Soups').exists())

    def test_menu_item_list_defaults_to_available_and_in_stock_items(self):
        response = self.clerk_client.get(self.items_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [row['name'] for row in response.data]
        self.assertIn('Pepper Soup', names)
        self.assertIn('Chicken', names)
        self.assertNotIn('Malt', names)
        self.assertNotIn('Fish', names)

    def test_menu_item_list_can_include_unavailable_and_out_of_stock(self):
        response = self.clerk_client.get(self.items_url, {'available_only': 'false'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [row['name'] for row in response.data]
        self.assertIn('Pepper Soup', names)
        self.assertIn('Malt', names)
        self.assertIn('Fish', names)
        self.assertIn('Chicken', names)

    def test_by_category_returns_only_active_categories_with_items(self):
        url = reverse('menu:menuitem-by-category')
        response = self.clerk_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['category']['name'], 'Active Cat')

    def test_toggle_availability_is_admin_only(self):
        url = reverse('menu:menuitem-toggle-availability', args=[self.available_item.menuItemId])
        clerk_response = self.clerk_client.post(url)
        self.assertEqual(clerk_response.status_code, status.HTTP_403_FORBIDDEN)

        admin_response = self.admin_client.post(url)
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
        self.available_item.refresh_from_db()
        self.assertFalse(self.available_item.isAvailable)

    def test_stock_info_returns_message_for_non_tracked_item(self):
        url = reverse('menu:menuitem-stock-info', args=[self.available_item.menuItemId])
        response = self.clerk_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'This item does not track stock')

    def test_stock_info_returns_404_when_tracked_item_missing_stock_record(self):
        tracked_item_no_stock = MenuItem.objects.create(
            category=self.active_category,
            name='Goat Meat',
            price='5000.00',
            isAvailable=True,
            trackStock=True,
        )
        url = reverse('menu:menuitem-stock-info', args=[tracked_item_no_stock.menuItemId])
        response = self.clerk_client.get(url, {'available_only': 'false'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'Stock information not found')

    def test_stock_info_returns_stock_payload_when_record_exists(self):
        url = reverse('menu:menuitem-stock-info', args=[self.tracked_in_stock_item.menuItemId])
        response = self.clerk_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['quantity'], 2)

    def test_stock_list_is_readable_by_any_authenticated_user(self):
        response = self.clerk_client.get(self.stock_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_stock_create_requires_admin_or_inventory_manager(self):
        payload = {
            'menuItem': str(self.available_item.menuItemId),
            'quantity': 10,
            'lowStockThreshold': 2,
            'unit': 'units',
        }
        response = self.clerk_client.post(self.stock_url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_low_stock_and_out_of_stock_endpoints(self):
        low_stock_url = reverse('menu:stock-low-stock')
        out_of_stock_url = reverse('menu:stock-out-of-stock')

        low_response = self.clerk_client.get(low_stock_url)
        out_response = self.clerk_client.get(out_of_stock_url)

        self.assertEqual(low_response.status_code, status.HTTP_200_OK)
        self.assertEqual(out_response.status_code, status.HTTP_200_OK)

        low_names = [row['menu_item_name'] for row in low_response.data]
        out_names = [row['menu_item_name'] for row in out_response.data]

        self.assertIn('Fish', low_names)
        self.assertIn('Chicken', low_names)
        self.assertIn('Fish', out_names)
        self.assertNotIn('Chicken', out_names)

    def test_adjust_stock_rejects_invalid_adjustment(self):
        url = reverse('menu:stock-adjust-stock', args=[self.stock_in.stockId])
        response = self.inventory_client.post(url, {'adjustment': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Invalid adjustment value')

    def test_adjust_stock_rejects_negative_result(self):
        url = reverse('menu:stock-adjust-stock', args=[self.stock_in.stockId])
        response = self.inventory_client.post(url, {'adjustment': -10})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Adjustment would result in negative stock')

    def test_adjust_stock_updates_quantity_and_logs_transaction(self):
        url = reverse('menu:stock-adjust-stock', args=[self.stock_in.stockId])
        response = self.inventory_client.post(url, {'adjustment': 3, 'note': 'Correction'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.stock_in.refresh_from_db()
        self.assertEqual(self.stock_in.quantity, 5)

        tx = StockTransaction.objects.filter(
            stock=self.stock_in,
            transactionType=StockTransaction.TransactionType.ADJUSTMENT,
        ).latest('createdAt')
        self.assertEqual(tx.quantityChanged, 3)
        self.assertEqual(tx.quantityBefore, 2)
        self.assertEqual(tx.quantityAfter, 5)
        self.assertEqual(tx.performedBy, self.inventory_manager)

    def test_restock_rejects_invalid_and_non_positive_quantity(self):
        url = reverse('menu:stock-restock', args=[self.stock_out.stockId])

        invalid_response = self.inventory_client.post(url, {'quantity': 'abc'})
        self.assertEqual(invalid_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_response.data['error'], 'Invalid quantity')

        non_positive_response = self.inventory_client.post(url, {'quantity': 0})
        self.assertEqual(non_positive_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            non_positive_response.data['error'],
            'Quantity must be a positive integer',
        )

    def test_restock_updates_quantity_and_logs_transaction(self):
        url = reverse('menu:stock-restock', args=[self.stock_out.stockId])
        response = self.inventory_client.post(url, {'quantity': 5, 'note': 'Supplier delivery'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.stock_out.refresh_from_db()
        self.assertEqual(self.stock_out.quantity, 5)

        tx = StockTransaction.objects.filter(
            stock=self.stock_out,
            transactionType=StockTransaction.TransactionType.RESTOCK,
        ).latest('createdAt')
        self.assertEqual(tx.quantityChanged, 5)
        self.assertEqual(tx.quantityBefore, 0)
        self.assertEqual(tx.quantityAfter, 5)
        self.assertEqual(tx.performedBy, self.inventory_manager)

    def test_stock_transactions_endpoint_is_admin_only(self):
        clerk_response = self.clerk_client.get(self.stock_transactions_url)
        self.assertEqual(clerk_response.status_code, status.HTTP_403_FORBIDDEN)

        admin_response = self.admin_client.get(self.stock_transactions_url)
        self.assertEqual(admin_response.status_code, status.HTTP_200_OK)
