# orders/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from .models import Receipt, Order, Payment
from .serializers import (
    ReceiptSerializer, ReceiptDetailSerializer,
    OrderSerializer, OrderCreateSerializer, PaymentSerializer,
)
from .services import ReceiptService
from accounts.permissions import IsAdmin
from notifications.services import NotificationService


class ReceiptViewSet(viewsets.ReadOnlyModelViewSet):
    queryset           = Receipt.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ReceiptDetailSerializer
        return ReceiptSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'Administrator':
            return Receipt.objects.all()
        return Receipt.objects.filter(order__takenBy=user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def print_receipt(self, request, pk=None):
        receipt           = self.get_object()
        receipt.printCount += 1
        receipt.printedAt  = timezone.now()
        receipt.printedBy  = request.user
        receipt.save(update_fields=['printCount', 'printedAt', 'printedBy'])
        return Response({
            'message': f'Receipt printed ({receipt.printCount} times)',
            'receipt': ReceiptDetailSerializer(receipt).data,
        })

    @action(detail=True, methods=['get'])
    def text_format(self, request, pk=None):
        receipt = self.get_object()
        return Response({
            'receiptNumber': receipt.receiptNumber,
            'format':        'text',
            'content':       receipt.receiptText,
        })

    @action(detail=True, methods=['get'])
    def html_format(self, request, pk=None):
        receipt = self.get_object()
        return Response({
            'receiptNumber': receipt.receiptNumber,
            'format':        'html',
            'content':       receipt.receiptHTML,
        })

    @action(detail=False, methods=['post'])
    def generate_for_order(self, request):
        order_id    = request.data.get('order_id')
        format_type = request.data.get('format', 'Thermal')

        try:
            order = Order.objects.get(orderId=order_id)
        except Order.DoesNotExist:
            return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)

        if request.user.role != 'Administrator' and order.takenBy != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)

        # Return existing receipt if already generated
        try:
            receipt = Receipt.objects.get(order=order)
            return Response({
                'message': 'Receipt already exists',
                'receipt': ReceiptSerializer(receipt).data,
            })
        except Receipt.DoesNotExist:
            pass

        receipt = ReceiptService.generate_receipt(order, format=format_type)
        return Response({
            'message': 'Receipt generated successfully',
            'receipt': ReceiptDetailSerializer(receipt).data,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def send_digital(self, request, pk=None):
        receipt = self.get_object()
        receipt.isDigitallySent = True
        receipt.save(update_fields=['isDigitallySent'])
        return Response({
            'message': 'Receipt marked as digitally sent',
            'receipt': ReceiptSerializer(receipt).data,
        })


class OrderViewSet(viewsets.ModelViewSet):
    queryset           = Order.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        user = self.request.user
        # ── Bug Fix #12: admins see all; others see their own orders ──────
        # Original code hid everything from non-admins on some paths.
        # Now clerks can always see the orders they took.
        if user.role == 'Administrator':
            return Order.objects.prefetch_related('items__menuItem').all()
        return Order.objects.prefetch_related('items__menuItem').filter(takenBy=user)

    def perform_create(self, serializer):
        serializer.save(takenBy=self.request.user)

    @action(detail=False, methods=['get'])
    def outstanding(self, request):
        qs = self.get_queryset().filter(
            paymentStatus__in=[Order.PaymentStatus.UNPAID, Order.PaymentStatus.PARTIAL]
        )
        return Response(OrderSerializer(qs, many=True).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def approve_credit(self, request, pk=None):
        order = self.get_object()
        if order.balance_due <= 0:
            return Response(
                {'error': 'Order has no outstanding balance'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.authorize_credit(request.user)
        NotificationService.create_credit_notification(order, request.user)
        return Response({
            'message': 'Deferred payment approved',
            'order':   OrderSerializer(order).data,
        })


class PaymentViewSet(viewsets.ModelViewSet):
    queryset           = Payment.objects.all()
    serializer_class   = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'Administrator':
            return Payment.objects.all()
        return Payment.objects.filter(processedBy=user)

    def get_permissions(self):
        if self.action == 'verify':
            return [IsAuthenticated(), IsAdmin()]
        return super().get_permissions()

    def perform_create(self, serializer):
        serializer.save(processedBy=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def verify(self, request, pk=None):
        payment = self.get_object()
        if payment.verificationStatus == Payment.VerificationStatus.CONFIRMED:
            return Response({
                'message': 'Payment already verified',
                'payment': PaymentSerializer(payment).data,
            })
        payment.verificationStatus = Payment.VerificationStatus.CONFIRMED
        payment.save(update_fields=['verificationStatus'])
        return Response({
            'message': 'Payment verified successfully',
            'payment': PaymentSerializer(payment).data,
        })