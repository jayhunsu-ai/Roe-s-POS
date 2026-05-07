from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import Staff
from menu.models import MenuItem
from orders.models import Customer, Order, OrderItem, Payment, Receipt
from orders.serializers import OrderSerializer, PaymentSerializer, ReceiptSerializer


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


class OrderModelTests(TestCase):
    def setUp(self):
        self.admin = make_staff('admin@pos.com', 'Admin', Staff.Roles.ADMIN)
        self.clerk = make_staff('clerk@pos.com', 'Clerk', Staff.Roles.CLERK)
        self.customer = Customer.objects.create(name='John Doe', phone='08012345678')
        self.menu_item = MenuItem.objects.create(name='Burger', price=Decimal('1200.00'))

    def test_order_number_auto_generation(self):
        order = Order.objects.create(takenBy=self.clerk, totalAmount=Decimal('1200.00'))
        self.assertTrue(order.orderNumber.startswith('ORD-'))

    def test_customer_fields_auto_filled_from_customer_relation(self):
        order = Order.objects.create(
            customer=self.customer,
            takenBy=self.clerk,
            totalAmount=Decimal('0.00'),
        )
        self.assertEqual(order.customerName, 'John Doe')
        self.assertEqual(order.customerPhone, '08012345678')

    def test_recalculate_totals_from_items(self):
        order = Order.objects.create(
            takenBy=self.clerk,
            totalAmount=Decimal('0.00'),
            discountAmount=Decimal('200.00'),
            taxAmount=Decimal('50.00'),
        )
        OrderItem.objects.create(
            order=order,
            menuItem=self.menu_item,
            quantity=2,
            unitPrice=Decimal('1200.00'),
            lineTotal=Decimal('0.00'),
        )
        order.recalculate_totals()
        order.refresh_from_db()
        self.assertEqual(order.subtotal, Decimal('2400.00'))
        self.assertEqual(order.totalAmount, Decimal('2250.00'))

    def test_payment_aggregates_balance_and_verified_paid(self):
        order = Order.objects.create(takenBy=self.clerk, totalAmount=Decimal('3000.00'))
        Payment.objects.create(
            order=order,
            method=Payment.PaymentMethod.CASH,
            amountPaid=Decimal('1000.00'),
            processedBy=self.clerk,
            verificationStatus=Payment.VerificationStatus.CONFIRMED,
        )
        Payment.objects.create(
            order=order,
            method=Payment.PaymentMethod.TRANSFER,
            amountPaid=Decimal('500.00'),
            reference='TXN-1',
            processedBy=self.clerk,
            verificationStatus=Payment.VerificationStatus.PENDING,
        )
        self.assertEqual(order.total_paid, Decimal('1500.00'))
        self.assertEqual(order.verified_paid, Decimal('1000.00'))
        self.assertEqual(order.balance_due, Decimal('1500.00'))

    def test_authorize_credit_sets_credit_fields(self):
        order = Order.objects.create(takenBy=self.clerk, totalAmount=Decimal('100.00'))
        self.assertFalse(order.isCreditAllowed)
        order.authorize_credit(self.admin)
        order.refresh_from_db()
        self.assertTrue(order.isCreditAllowed)
        self.assertEqual(order.creditApprovedBy, self.admin)
        self.assertIsNotNone(order.creditApprovedAt)

    def test_payment_transfer_default_verification_status_matches_model_behavior(self):
        order = Order.objects.create(takenBy=self.clerk, totalAmount=Decimal('100.00'))
        payment = Payment.objects.create(
            order=order,
            method=Payment.PaymentMethod.TRANSFER,
            amountPaid=Decimal('100.00'),
            reference='TRF-REF',
            processedBy=self.clerk,
        )
        self.assertEqual(payment.verificationStatus, Payment.VerificationStatus.CONFIRMED)

    def test_receipt_number_auto_generation(self):
        order = Order.objects.create(takenBy=self.clerk, totalAmount=Decimal('100.00'))
        receipt = Receipt.objects.create(order=order, receiptContent={'ok': True})
        self.assertTrue(receipt.receiptNumber.startswith('REC-'))


class OrderSerializerTests(TestCase):
    def setUp(self):
        self.clerk = make_staff('clerk2@pos.com', 'Clerk 2', Staff.Roles.CLERK)
        self.order = Order.objects.create(takenBy=self.clerk, totalAmount=Decimal('1000.00'))
        self.payment = Payment.objects.create(
            order=self.order,
            method=Payment.PaymentMethod.CASH,
            amountPaid=Decimal('300.00'),
            processedBy=self.clerk,
        )
        self.receipt = Receipt.objects.create(order=self.order, receiptContent={'hello': 'world'})

    def test_order_serializer_includes_balance_fields(self):
        data = OrderSerializer(self.order).data
        self.assertEqual(data['amountPaid'], 300.0)
        self.assertEqual(data['verifiedPaid'], 300.0)
        self.assertEqual(data['balanceDue'], 700.0)

    def test_payment_serializer_transfer_requires_reference(self):
        serializer = PaymentSerializer(
            data={
                'order': self.order.orderId,
                'method': Payment.PaymentMethod.TRANSFER,
                'amountPaid': '100.00',
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn('reference', serializer.errors)

    def test_receipt_serializer_exposes_order_number(self):
        data = ReceiptSerializer(self.receipt).data
        self.assertEqual(data['orderNumber'], self.order.orderNumber)


class OrdersApiTests(APITestCase):
    def setUp(self):
        self.admin = make_staff('admin-api@pos.com', 'Admin API', Staff.Roles.ADMIN)
        self.clerk = make_staff('clerk-api@pos.com', 'Clerk API', Staff.Roles.CLERK)
        self.other_clerk = make_staff('other-clerk@pos.com', 'Other Clerk', Staff.Roles.CLERK)

        self.admin_client = auth_client(self.admin)
        self.clerk_client = auth_client(self.clerk)
        self.other_clerk_client = auth_client(self.other_clerk)

        self.order_mine = Order.objects.create(
            takenBy=self.clerk,
            paymentStatus=Order.PaymentStatus.UNPAID,
            totalAmount=Decimal('2000.00'),
        )
        self.order_other = Order.objects.create(
            takenBy=self.other_clerk,
            paymentStatus=Order.PaymentStatus.PARTIAL,
            totalAmount=Decimal('1000.00'),
        )

        self.my_payment = Payment.objects.create(
            order=self.order_mine,
            method=Payment.PaymentMethod.CASH,
            amountPaid=Decimal('500.00'),
            processedBy=self.clerk,
            verificationStatus=Payment.VerificationStatus.CONFIRMED,
        )
        self.transfer_payment = Payment.objects.create(
            order=self.order_mine,
            method=Payment.PaymentMethod.TRANSFER,
            amountPaid=Decimal('250.00'),
            reference='TRX-001',
            processedBy=self.clerk,
            verificationStatus=Payment.VerificationStatus.PENDING,
        )
        self.other_payment = Payment.objects.create(
            order=self.order_other,
            method=Payment.PaymentMethod.CARD,
            amountPaid=Decimal('700.00'),
            processedBy=self.other_clerk,
            verificationStatus=Payment.VerificationStatus.CONFIRMED,
        )

        self.receipt_mine = Receipt.objects.create(
            order=self.order_mine,
            receiptContent={'items': []},
            receiptText='TEXT RECEIPT',
            receiptHTML='<p>HTML RECEIPT</p>',
        )
        self.receipt_other = Receipt.objects.create(
            order=self.order_other,
            receiptContent={'items': []},
            receiptText='OTHER TEXT',
            receiptHTML='<p>OTHER HTML</p>',
        )

        self.orders_url = reverse('orders:order-list')
        self.payments_url = reverse('orders:payment-list')
        self.receipts_url = reverse('orders:receipt-list')

    def test_orders_list_visibility_by_role(self):
        admin_res = self.admin_client.get(self.orders_url)
        clerk_res = self.clerk_client.get(self.orders_url)
        self.assertEqual(admin_res.status_code, status.HTTP_200_OK)
        self.assertEqual(clerk_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(admin_res.data), 2)
        self.assertEqual(len(clerk_res.data), 1)
        self.assertEqual(clerk_res.data[0]['orderNumber'], self.order_mine.orderNumber)

    def test_orders_outstanding_returns_unpaid_or_partial(self):
        url = reverse('orders:order-outstanding')
        admin_res = self.admin_client.get(url)
        clerk_res = self.clerk_client.get(url)
        self.assertEqual(admin_res.status_code, status.HTTP_200_OK)
        self.assertEqual(clerk_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(admin_res.data), 2)
        self.assertEqual(len(clerk_res.data), 1)

    def test_approve_credit_admin_only_and_requires_balance(self):
        url = reverse('orders:order-approve-credit', args=[self.order_mine.orderId])
        clerk_res = self.clerk_client.post(url)
        self.assertEqual(clerk_res.status_code, status.HTTP_403_FORBIDDEN)

        admin_res = self.admin_client.post(url)
        self.assertEqual(admin_res.status_code, status.HTTP_200_OK)
        self.order_mine.refresh_from_db()
        self.assertTrue(self.order_mine.isCreditAllowed)
        self.assertEqual(self.order_mine.creditApprovedBy, self.admin)

    def test_approve_credit_rejects_when_no_balance(self):
        fully_paid_order = Order.objects.create(
            takenBy=self.clerk,
            totalAmount=Decimal('100.00'),
            paymentStatus=Order.PaymentStatus.PAID,
        )
        Payment.objects.create(
            order=fully_paid_order,
            method=Payment.PaymentMethod.CASH,
            amountPaid=Decimal('100.00'),
            processedBy=self.clerk,
            verificationStatus=Payment.VerificationStatus.CONFIRMED,
        )
        url = reverse('orders:order-approve-credit', args=[fully_paid_order.orderId])
        res = self.admin_client.post(url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data['error'], 'Order has no outstanding balance')

    def test_payments_list_visibility_by_role(self):
        admin_res = self.admin_client.get(self.payments_url)
        clerk_res = self.clerk_client.get(self.payments_url)
        self.assertEqual(admin_res.status_code, status.HTTP_200_OK)
        self.assertEqual(clerk_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(admin_res.data), 3)
        self.assertEqual(len(clerk_res.data), 2)

    def test_create_payment_sets_processed_by_to_request_user(self):
        payload = {
            'order': str(self.order_mine.orderId),
            'method': Payment.PaymentMethod.CASH,
            'amountPaid': '100.00',
        }
        res = self.clerk_client.post(self.payments_url, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        created = Payment.objects.get(paymentId=res.data['paymentId'])
        self.assertEqual(created.processedBy, self.clerk)

    def test_verify_payment_admin_only(self):
        url = reverse('orders:payment-verify', args=[self.transfer_payment.paymentId])

        clerk_res = self.clerk_client.post(url)
        self.assertEqual(clerk_res.status_code, status.HTTP_403_FORBIDDEN)

        admin_res = self.admin_client.post(url)
        self.assertEqual(admin_res.status_code, status.HTTP_200_OK)
        self.transfer_payment.refresh_from_db()
        self.assertEqual(
            self.transfer_payment.verificationStatus,
            Payment.VerificationStatus.CONFIRMED,
        )

    def test_verify_payment_returns_message_when_already_confirmed(self):
        url = reverse('orders:payment-verify', args=[self.my_payment.paymentId])
        res = self.admin_client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['message'], 'Payment already verified')

    def test_receipts_list_visibility_by_role(self):
        admin_res = self.admin_client.get(self.receipts_url)
        clerk_res = self.clerk_client.get(self.receipts_url)
        self.assertEqual(admin_res.status_code, status.HTTP_200_OK)
        self.assertEqual(clerk_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(admin_res.data), 2)
        self.assertEqual(len(clerk_res.data), 1)
        self.assertEqual(clerk_res.data[0]['orderNumber'], self.order_mine.orderNumber)

    def test_print_receipt_admin_only(self):
        url = reverse('orders:receipt-print-receipt', args=[self.receipt_mine.receiptId])
        clerk_res = self.clerk_client.post(url)
        self.assertEqual(clerk_res.status_code, status.HTTP_403_FORBIDDEN)

        admin_res = self.admin_client.post(url)
        self.assertEqual(admin_res.status_code, status.HTTP_200_OK)
        self.receipt_mine.refresh_from_db()
        self.assertEqual(self.receipt_mine.printCount, 1)
        self.assertEqual(self.receipt_mine.printedBy, self.admin)

    def test_receipt_text_and_html_format_endpoints(self):
        text_url = reverse('orders:receipt-text-format', args=[self.receipt_mine.receiptId])
        html_url = reverse('orders:receipt-html-format', args=[self.receipt_mine.receiptId])
        text_res = self.clerk_client.get(text_url)
        html_res = self.clerk_client.get(html_url)
        self.assertEqual(text_res.status_code, status.HTTP_200_OK)
        self.assertEqual(html_res.status_code, status.HTTP_200_OK)
        self.assertEqual(text_res.data['format'], 'text')
        self.assertEqual(html_res.data['format'], 'html')

    def test_generate_receipt_for_order_validates_permissions_and_not_found(self):
        url = reverse('orders:receipt-generate-for-order')
        not_found_res = self.clerk_client.post(url, {'order_id': '00000000-0000-0000-0000-000000000000'})
        self.assertEqual(not_found_res.status_code, status.HTTP_404_NOT_FOUND)

        order_other_without_receipt = Order.objects.create(
            takenBy=self.other_clerk,
            totalAmount=Decimal('500.00'),
            paymentStatus=Order.PaymentStatus.UNPAID,
        )
        forbidden_res = self.clerk_client.post(url, {'order_id': str(order_other_without_receipt.orderId)})
        self.assertEqual(forbidden_res.status_code, status.HTTP_403_FORBIDDEN)

    def test_generate_receipt_for_order_returns_existing_receipt(self):
        url = reverse('orders:receipt-generate-for-order')
        res = self.clerk_client.post(url, {'order_id': str(self.order_mine.orderId)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['message'], 'Receipt already exists')

    def test_send_digital_marks_receipt_as_sent(self):
        url = reverse('orders:receipt-send-digital', args=[self.receipt_mine.receiptId])
        res = self.clerk_client.post(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.receipt_mine.refresh_from_db()
        self.assertTrue(self.receipt_mine.isDigitallySent)
