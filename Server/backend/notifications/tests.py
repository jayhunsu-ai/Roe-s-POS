from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import Staff
from inventory.models import InventoryItem, Supplier
from notifications.models import Notification, NotificationPreference
from notifications.serializers import (
    NotificationDetailSerializer,
    NotificationListSerializer,
    NotificationPreferenceSerializer,
)
from notifications.services import NotificationService
from orders.models import Order, Payment


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


class NotificationModelTests(TestCase):
    def setUp(self):
        self.admin = make_staff('admin@pos.com', 'Admin User', Staff.Roles.ADMIN)

    def test_notification_and_preference_string_representation(self):
        preference = NotificationPreference.objects.create(staff=self.admin)
        notification = Notification.objects.create(
            type=Notification.NotificationType.SYSTEM_ERROR,
            title='System Alert',
            message='Test notification',
            targetAdmin=self.admin,
        )
        self.assertTrue(preference.notify_system)
        self.assertEqual(str(preference), 'Preferences for Admin User')
        self.assertEqual(str(notification), 'System Error - System Alert')

    def test_mark_as_read_sets_status_and_read_at(self):
        notification = Notification.objects.create(
            type=Notification.NotificationType.SYSTEM_ERROR,
            title='Error',
            message='Failure',
            targetAdmin=self.admin,
        )
        self.assertEqual(notification.status, Notification.NotificationStatus.UNREAD)
        self.assertIsNone(notification.readAt)
        notification.mark_as_read()
        notification.refresh_from_db()
        self.assertEqual(notification.status, Notification.NotificationStatus.READ)
        self.assertIsNotNone(notification.readAt)


class NotificationSerializerTests(TestCase):
    def setUp(self):
        self.admin = make_staff('serializer-admin@pos.com', 'Serializer Admin', Staff.Roles.ADMIN)
        self.order = Order.objects.create(
            takenBy=self.admin,
            totalAmount=Decimal('1000.00'),
            paymentStatus=Order.PaymentStatus.UNPAID,
        )
        self.notification = Notification.objects.create(
            type=Notification.NotificationType.ORDER_PLACED,
            title='Order Created',
            message='Order is in system',
            targetAdmin=self.admin,
            order=self.order,
            priority=2,
        )
        self.preference = NotificationPreference.objects.create(staff=self.admin)

    def test_list_serializer_fields(self):
        data = NotificationListSerializer(self.notification).data
        self.assertEqual(data['type'], Notification.NotificationType.ORDER_PLACED)
        self.assertEqual(data['status'], Notification.NotificationStatus.UNREAD)
        self.assertIn('type_display', data)
        self.assertIn('status_display', data)

    def test_detail_serializer_includes_order_number(self):
        data = NotificationDetailSerializer(self.notification).data
        self.assertEqual(data['order_number'], self.order.orderNumber)
        self.assertEqual(data['priority'], 2)

    def test_preference_serializer_fields(self):
        data = NotificationPreferenceSerializer(self.preference).data
        self.assertEqual(data['staff_name'], 'Serializer Admin')
        self.assertTrue(data['notify_low_stock'])
        self.assertIn('updatedAt', data)


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.admin = make_staff('service-admin@pos.com', 'Service Admin', Staff.Roles.ADMIN)
        self.clerk = make_staff('service-clerk@pos.com', 'Service Clerk', Staff.Roles.CLERK)
        self.supplier = Supplier.objects.create(name='Vendor')
        self.item = InventoryItem.objects.create(
            name='Tomatoes',
            unit=InventoryItem.Unit.KG,
            quantityInStock=Decimal('2.00'),
            lowStockThreshold=Decimal('5.00'),
            costPerUnit=Decimal('200.00'),
            supplier=self.supplier,
        )
        self.order = Order.objects.create(
            takenBy=self.clerk,
            customerName='Walk-in',
            totalAmount=Decimal('5000.00'),
            paymentStatus=Order.PaymentStatus.UNPAID,
        )
        Notification.objects.all().delete()

    def test_low_stock_notification_respects_preferences(self):
        NotificationPreference.objects.create(staff=self.admin, notify_low_stock=False)
        NotificationService.create_low_stock_notification(self.item)
        self.assertEqual(Notification.objects.count(), 0)

        pref = self.admin.notification_preference
        pref.notify_low_stock = True
        pref.save(update_fields=['notify_low_stock'])
        NotificationService.create_low_stock_notification(self.item)
        self.assertEqual(Notification.objects.count(), 1)
        notif = Notification.objects.first()
        self.assertEqual(notif.type, Notification.NotificationType.LOW_STOCK)
        self.assertEqual(notif.targetAdmin, self.admin)

    def test_payment_notification_type_changes_with_transfer_pending(self):
        payment = Payment.objects.create(
            order=self.order,
            method=Payment.PaymentMethod.TRANSFER,
            amountPaid=Decimal('1000.00'),
            reference='TRX-123',
            processedBy=self.clerk,
            verificationStatus=Payment.VerificationStatus.PENDING,
        )
        Notification.objects.all().delete()
        NotificationService.create_payment_notification(self.order, payment)
        notif = Notification.objects.first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.type, Notification.NotificationType.PAYMENT_PENDING)

    def test_system_notification_targets_admins(self):
        NotificationService.create_system_notification('DB Error', 'Database unavailable', priority=5)
        notif = Notification.objects.first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.type, Notification.NotificationType.SYSTEM_ERROR)
        self.assertEqual(notif.priority, 5)
        self.assertEqual(notif.targetAdmin, self.admin)


class NotificationApiTests(APITestCase):
    def setUp(self):
        self.admin = make_staff('api-admin@pos.com', 'API Admin', Staff.Roles.ADMIN)
        self.clerk = make_staff('api-clerk@pos.com', 'API Clerk', Staff.Roles.CLERK)
        self.admin_client = auth_client(self.admin)
        self.clerk_client = auth_client(self.clerk)

        self.targeted_notification = Notification.objects.create(
            type=Notification.NotificationType.ORDER_PLACED,
            title='Targeted',
            message='Targeted to admin',
            targetAdmin=self.admin,
            status=Notification.NotificationStatus.UNREAD,
        )
        self.global_notification = Notification.objects.create(
            type=Notification.NotificationType.SYSTEM_ERROR,
            title='Global',
            message='For all admins',
            targetAdmin=None,
            status=Notification.NotificationStatus.UNREAD,
        )
        self.archived_notification = Notification.objects.create(
            type=Notification.NotificationType.PAYMENT_RECEIVED,
            title='Archived',
            message='Already archived',
            targetAdmin=self.admin,
            status=Notification.NotificationStatus.ARCHIVED,
        )

        self.list_url = reverse('notifications:notification-list')

    def test_admin_can_list_targeted_and_global_notifications(self):
        response = self.admin_client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_non_admin_gets_empty_notification_list(self):
        response = self.clerk_client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_unread_endpoint_returns_count_and_collection(self):
        url = reverse('notifications:notification-unread')
        response = self.admin_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['notifications']), 2)

    def test_by_type_requires_query_param(self):
        url = reverse('notifications:notification-by-type')
        response = self.admin_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'type parameter is required')

    def test_by_type_filters_notifications(self):
        url = reverse('notifications:notification-by-type')
        response = self.admin_client.get(url, {'type': Notification.NotificationType.ORDER_PLACED})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Targeted')

    def test_mark_as_read_endpoint(self):
        url = reverse('notifications:notification-mark-as-read', args=[self.targeted_notification.notificationId])
        response = self.admin_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.targeted_notification.refresh_from_db()
        self.assertEqual(self.targeted_notification.status, Notification.NotificationStatus.READ)
        self.assertIsNotNone(self.targeted_notification.readAt)

    def test_mark_all_read_endpoint(self):
        url = reverse('notifications:notification-mark-all-read')
        response = self.admin_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('notifications marked as read', response.data['message'])
        unread_count = Notification.objects.filter(
            targetAdmin__in=[self.admin, None],
            status=Notification.NotificationStatus.UNREAD,
        ).count()
        self.assertEqual(unread_count, 0)

    def test_archive_endpoint(self):
        url = reverse('notifications:notification-archive', args=[self.global_notification.notificationId])
        response = self.admin_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.global_notification.refresh_from_db()
        self.assertEqual(self.global_notification.status, Notification.NotificationStatus.ARCHIVED)

    def test_stats_endpoint(self):
        url = reverse('notifications:notification-stats')
        response = self.admin_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 3)
        self.assertEqual(response.data['unread'], 2)
        self.assertIn('by_type', response.data)


class NotificationPreferencesApiTests(APITestCase):
    def setUp(self):
        self.admin = make_staff('prefs-admin@pos.com', 'Prefs Admin', Staff.Roles.ADMIN)
        self.clerk = make_staff('prefs-clerk@pos.com', 'Prefs Clerk', Staff.Roles.CLERK)
        self.admin_client = auth_client(self.admin)
        self.clerk_client = auth_client(self.clerk)

        self.my_pref_url = reverse('notifications:my_preferences')
        self.staff_pref_url = reverse('notifications:staff_preferences', args=[self.admin.staffId])

    def test_admin_can_get_own_preferences(self):
        response = self.admin_client.get(self.my_pref_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['staff_name'], 'Prefs Admin')

    def test_admin_can_update_own_preferences(self):
        response = self.admin_client.put(self.my_pref_url, {'notify_orders': False}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        pref = NotificationPreference.objects.get(staff=self.admin)
        self.assertFalse(pref.notify_orders)

    def test_admin_can_get_other_staff_preferences_by_staff_id(self):
        NotificationPreference.objects.create(staff=self.clerk)
        url = reverse('notifications:staff_preferences', args=[self.clerk.staffId])
        response = self.admin_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['staff_name'], 'Prefs Clerk')

    def test_non_admin_cannot_access_preferences_endpoints(self):
        response = self.clerk_client.get(self.my_pref_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
