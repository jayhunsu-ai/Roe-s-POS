from django.test import TestCase
from django.utils import timezone
from datetime import date, timedelta
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse

from analytics.models import (
    SalesSummary,
    ItemPerformance,
    HourlyAnalytics,
    StaffPerformance,
    InventoryAnalytics
)
from analytics.serializers import (
    SalesSummarySerializer,
    ItemPerformanceSerializer,
    HourlyAnalyticsSerializer,
    StaffPerformanceSerializer,
    InventoryAnalyticsSerializer
)

from accounts.models import Staff
from menu.models import MenuItem
from inventory.models import InventoryItem
from orders.models import Order, OrderItem


# =========================
# TEST SETUP MIXIN
# =========================
class AnalyticsTestMixin:
    def setUp(self):
        self.client = APIClient()

        # Admin user (required by IsAdmin permission)
        self.admin = Staff.objects.create_user(
            email="admin@test.com",
            staffName="Admin User",
            password="123456",
            role=Staff.Roles.ADMIN
        )

        self.client.force_authenticate(user=self.admin)

        # Sample menu item
        self.menu_item = MenuItem.objects.create(
            name="Burger",
            price=1000
        )

        # Inventory item
        self.inventory_item = InventoryItem.objects.create(
            name="Rice",
            quantityInStock=100
        )

        # Staff
        self.staff = Staff.objects.create_user(
            email="staff@test.com",
            staffName="Staff One",
            password="123456",
            role=Staff.Roles.CLERK
        )

        self.today = timezone.now().date()


# =========================
# MODEL TESTS
# =========================
class AnalyticsModelTests(AnalyticsTestMixin, TestCase):

    def test_sales_summary_str(self):
        obj = SalesSummary.objects.create(
            periodType=SalesSummary.PeriodType.DAILY,
            startDate=self.today,
            endDate=self.today
        )
        self.assertIn("Daily Summary", str(obj))

    def test_item_performance_str(self):
        obj = ItemPerformance.objects.create(
            menuItem=self.menu_item,
            date=self.today,
            quantitySold=5
        )
        self.assertIn("Burger", str(obj))

    def test_hourly_analytics_str(self):
        obj = HourlyAnalytics.objects.create(
            date=self.today,
            hour=14,
            revenue=2000
        )
        self.assertIn("14:00", str(obj))

    def test_staff_performance_str(self):
        obj = StaffPerformance.objects.create(
            staff=self.staff,
            date=self.today,
            totalRevenue=5000
        )
        self.assertIn("Staff One", str(obj))

    def test_inventory_analytics_str(self):
        obj = InventoryAnalytics.objects.create(
            inventoryItem=self.inventory_item,
            date=self.today,
            stockUsed=20
        )
        self.assertIn("Rice", str(obj))


# =========================
# SERIALIZER TESTS
# =========================
class AnalyticsSerializerTests(AnalyticsTestMixin, TestCase):

    def test_sales_summary_serializer(self):
        obj = SalesSummary.objects.create(
            periodType=SalesSummary.PeriodType.DAILY,
            startDate=self.today,
            endDate=self.today
        )
        data = SalesSummarySerializer(obj).data
        self.assertEqual(data["periodType"], "Daily")

    def test_item_performance_serializer(self):
        obj = ItemPerformance.objects.create(
            menuItem=self.menu_item,
            date=self.today,
            quantitySold=10,
            revenue=10000
        )
        data = ItemPerformanceSerializer(obj).data
        self.assertEqual(data["item_name"], "Burger")
        self.assertEqual(data["quantitySold"], 10)

    def test_hourly_serializer(self):
        obj = HourlyAnalytics.objects.create(
            date=self.today,
            hour=10,
            revenue=3000
        )
        data = HourlyAnalyticsSerializer(obj).data
        self.assertEqual(data["hour"], 10)

    def test_staff_performance_serializer(self):
        obj = StaffPerformance.objects.create(
            staff=self.staff,
            date=self.today,
            totalRevenue=7000
        )
        data = StaffPerformanceSerializer(obj).data
        self.assertEqual(data["staff_name"], "Staff One")

    def test_inventory_serializer(self):
        obj = InventoryAnalytics.objects.create(
            inventoryItem=self.inventory_item,
            date=self.today,
            stockUsed=15
        )
        data = InventoryAnalyticsSerializer(obj).data
        self.assertEqual(data["item_name"], "Rice")


# =========================
# VIEWSET TESTS
# =========================
class AnalyticsViewSetTests(AnalyticsTestMixin, TestCase):

    def create_fake_orders(self):
        """Create minimal fake order data for dashboard tests"""
        order = Order.objects.create(
            totalAmount=5000,
            status="Paid",
            createdAt=timezone.now()
        )

        OrderItem.objects.create(
            order=order,
            menuItem=self.menu_item,
            quantity=2,
            unitPrice=1000,
            lineTotal=2000
        )

    def test_dashboard_endpoint(self):
        self.create_fake_orders()
        url =reverse('analytics-dashboard')
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("summary", res.data)
        self.assertIn("top_items", res.data)
        self.assertIn("alerts", res.data)

    def test_sales_report_missing_params(self):
        url =reverse('analytics-sales-report')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 400)

    def test_sales_report_valid(self):
        url = reverse('analytics-sales-report')
        res = self.client.get(url, {
            'start_date': self.today.isoformat(),
            'end_date': self.today.isoformat()
            })
        self.assertEqual(res.status_code, 200)
        self.assertIn("summary", res.data)

        

    def test_item_performance_endpoint(self):
        ItemPerformance.objects.create(
            menuItem=self.menu_item,
            date=self.today,
            quantitySold=5,
            revenue=5000
        )
        url = reverse('analytics-item-performance')
        res = self.client.get(url, {'days': 30})
        self.assertEqual(res.status_code, 200)
        self.assertIn("items", res.data)

    def test_peak_hours_endpoint(self):
        HourlyAnalytics.objects.create(
            date=self.today,
            hour=12,
            revenue=2000,
            orderCount=5
        )
        url = reverse('analytics-peak-hours')

        res = self.client.get(url, {'days': 7})
        self.assertEqual(res.status_code, 200)
        self.assertIn("hourly_breakdown", res.data)

    def test_staff_performance_endpoint(self):
        StaffPerformance.objects.create(
            staff=self.staff,
            date=self.today,
            totalRevenue=8000,
            ordersTaken=10
        )
        url = reverse('analytics-staff-performance')
        res = self.client.get(url,{'days': 30})
        self.assertEqual(res.status_code, 200)
        self.assertIn("staff", res.data)


# =========================
# EDGE CASE TESTS
# =========================
class AnalyticsEdgeCaseTests(AnalyticsTestMixin, TestCase):

    def test_percentage_change_zero_previous(self):
        from analytics.views import AnalyticsViewSet

        view = AnalyticsViewSet()
        self.assertEqual(view._calculate_percentage_change(100, 0), 100.0)
        self.assertEqual(view._calculate_percentage_change(0, 0), 0.0)

    def test_empty_dashboard_does_not_crash(self):
        url = reverse('analytics-dashboard')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertIsInstance(res.data, dict)