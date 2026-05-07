# orders/serializers.py
from decimal import Decimal

from rest_framework import serializers
from .models import Receipt, Order, Payment, OrderItem
from menu.models import MenuItem


class OrderItemSerializer(serializers.ModelSerializer):
    menuItemName = serializers.SerializerMethodField()

    class Meta:
        model  = OrderItem
        fields = [
            'orderItemId', 'menuItem', 'menuItemName',
            'quantity', 'unitPrice', 'lineTotal', 'note',
        ]
        read_only_fields = ['orderItemId', 'lineTotal', 'unitPrice']

    def get_menuItemName(self, obj):
        return obj.menuItem.name if obj.menuItem else obj.menuItemName


class OrderItemCreateSerializer(serializers.Serializer):
    """
    Bug Fix #8 — original code passed raw item dicts straight to
    OrderItem.objects.create(), meaning 'menuItem' arrived as a UUID string
    and caused an IntegrityError.  This serializer resolves the FK properly.
    """
    menuItem  = serializers.PrimaryKeyRelatedField(queryset=MenuItem.objects.all())
    quantity  = serializers.IntegerField(min_value=1)
    notes     = serializers.CharField(required=False, allow_blank=True, default='')


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True, write_only=True)

    class Meta:
        model  = Order
        fields = [
            'orderType', 'status', 'paymentStatus', 'paymentMethod',
            'tableNumber', 'customerName', 'customerPhone',
            'note', 'totalAmount', 'items',
        ]
        read_only_fields = [
            'orderId', 'orderNumber',
            'subtotal', 'discountAmount', 'taxAmount',
        ]

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        validated_data.pop('totalAmount', None)   # recalculated from items
        request = self.context.get('request')
        validated_data['takenBy'] = request.user

        order = Order.objects.create(**validated_data)

        for item_data in items_data:
            OrderItem.objects.create(
                order    = order,
                menuItem = item_data['menuItem'],   # already a MenuItem instance
                quantity = item_data['quantity'],
                note     = item_data.get('notes', ''),
                # unitPrice + lineTotal auto-set in OrderItem.save()
                unitPrice=item_data['menuItem'].price,
            )

        order.recalculate_totals()

        if (
            order.status == Order.OrderStatus.COMPLETED and
            order.paymentStatus == Order.PaymentStatus.PAID and
            not Payment.objects.filter(order=order).exists()
        ):
            Payment.objects.create(
                order=order,
                method=order.paymentMethod or Payment.PaymentMethod.CASH,
                amountPaid=Decimal(str(order.totalAmount)),
                amountChange=Decimal('0.00'),
                verificationStatus=Payment.VerificationStatus.CONFIRMED,
                processedBy=request.user,
            )

        return order


class ReceiptSerializer(serializers.ModelSerializer):
    orderNumber    = serializers.CharField(source='order.orderNumber', read_only=True)
    format_display = serializers.CharField(source='get_format_display', read_only=True)

    class Meta:
        model  = Receipt
        fields = [
            'receiptId', 'orderNumber', 'receiptNumber',
            'format', 'format_display',
            'printedAt', 'printCount', 'isDigitallySent', 'generatedAt',
        ]
        read_only_fields = ['receiptId', 'receiptNumber', 'generatedAt']


class ReceiptDetailSerializer(serializers.ModelSerializer):
    orderNumber    = serializers.CharField(source='order.orderNumber', read_only=True)
    format_display = serializers.CharField(source='get_format_display', read_only=True)

    class Meta:
        model  = Receipt
        fields = [
            'receiptId', 'orderNumber', 'receiptNumber',
            'format', 'format_display',
            'receiptContent', 'receiptHTML', 'receiptText',
            'printedAt', 'printCount', 'printedBy',
            'isDigitallySent', 'generatedAt', 'updatedAt',
        ]
        read_only_fields = [
            'receiptId', 'receiptNumber',
            'receiptContent', 'generatedAt', 'updatedAt',
        ]


class OrderSerializer(serializers.ModelSerializer):
    amountPaid           = serializers.SerializerMethodField()
    verifiedPaid         = serializers.SerializerMethodField()
    balanceDue           = serializers.SerializerMethodField()
    creditApprovedByName = serializers.CharField(source='creditApprovedBy.staffName', read_only=True)
    takenByName          = serializers.CharField(source='takenBy.staffName', read_only=True)
    servedByName         = serializers.CharField(source='servedBy.staffName', read_only=True)
    totalAmount          = serializers.SerializerMethodField()
    items                = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model  = Order
        fields = [
            'orderId', 'orderNumber', 'orderType', 'status',
            'paymentStatus', 'paymentMethod',
            'customerName', 'customerPhone', 'tableNumber',
            'takenByName', 'servedByName',
            'subtotal', 'discountAmount', 'taxAmount', 'totalAmount',
            'amountPaid', 'verifiedPaid', 'balanceDue',
            'items',
            'isCreditAllowed', 'creditApprovedByName', 'creditApprovedAt',
            'createdAt', 'updatedAt',
        ]
        read_only_fields = [
            'orderId', 'orderNumber', 'subtotal', 'totalAmount',
            'amountPaid', 'verifiedPaid', 'balanceDue',
            'takenByName', 'servedByName', 'items',
            'creditApprovedByName', 'creditApprovedAt',
            'createdAt', 'updatedAt',
        ]

    def get_amountPaid(self, obj):
        return float(obj.total_paid)

    def get_verifiedPaid(self, obj):
        return float(obj.verified_paid)

    def get_balanceDue(self, obj):
        return float(obj.balance_due)

    def get_totalAmount(self, obj):
        if obj.totalAmount > 0:
            return obj.totalAmount
        return sum(item.lineTotal for item in obj.items.all())


class PaymentSerializer(serializers.ModelSerializer):
    orderNumber     = serializers.CharField(source='order.orderNumber', read_only=True)
    processedByName = serializers.CharField(source='processedBy.staffName', read_only=True)
    isVerified      = serializers.SerializerMethodField()

    class Meta:
        model  = Payment
        fields = [
            'paymentId', 'order', 'orderNumber',
            'method', 'amountPaid', 'amountChange',
            'reference', 'processedBy', 'processedByName',
            'verificationStatus', 'isVerified', 'createdAt',
        ]
        read_only_fields = [
            'paymentId', 'orderNumber', 'processedBy',
            'processedByName', 'isVerified', 'createdAt',
        ]

    def validate(self, data):
        if data.get('method') == Payment.PaymentMethod.TRANSFER and not data.get('reference'):
            raise serializers.ValidationError(
                {'reference': 'Reference is required for bank transfers'}
            )
        return data

    def get_isVerified(self, obj):
        return obj.is_verified

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['processedBy'] = request.user
        return Payment.objects.create(**validated_data)