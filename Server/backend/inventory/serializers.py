from django.utils import timezone
from rest_framework import serializers

from orders.models import Order
from .models import (
    Supplier,
    InventoryItem,
    PurchaseOrder,
    PurchaseOrderItem,
    InventoryTransaction,
)


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = [
            'supplierId',
            'name',
            'contactName',
            'phone',
            'email',
            'address',
            'isActive',
            'createdAt',
        ]


class InventoryItemSerializer(serializers.ModelSerializer):
    supplier = SupplierSerializer(read_only=True)
    supplierId = serializers.PrimaryKeyRelatedField(
        queryset=Supplier.objects.all(), source='supplier', write_only=True, allow_null=True, required=False
    )
    isLowStock = serializers.BooleanField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            'inventoryItemId',
            'name',
            'description',
            'category',
            'unit',
            'quantityInStock',
            'lowStockThreshold',
            'costPerUnit',
            'supplier',
            'supplierId',
            'isActive',
            'createdAt',
            'updatedAt',
            'isLowStock',
        ]


class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    inventoryItem = InventoryItemSerializer(read_only=True)
    inventoryItemId = serializers.PrimaryKeyRelatedField(
        queryset=InventoryItem.objects.all(), source='inventoryItem', write_only=True
    )

    class Meta:
        model = PurchaseOrderItem
        fields = [
            'poItemId',
            'inventoryItem',
            'inventoryItemId',
            'quantityOrdered',
            'quantityReceived',
            'costPerUnit',
            'lineTotal',
        ]
        read_only_fields = ['lineTotal']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier = SupplierSerializer(read_only=True)
    supplierId = serializers.PrimaryKeyRelatedField(
        queryset=Supplier.objects.all(), source='supplier', write_only=True, allow_null=True, required=False
    )
    items = PurchaseOrderItemSerializer(many=True)
    orderedBy = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            'purchaseOrderId',
            'poNumber',
            'supplier',
            'supplierId',
            'status',
            'totalCost',
            'note',
            'orderedBy',
            'orderedAt',
            'receivedAt',
            'items',
            'createdAt',
            'updatedAt',
        ]
        read_only_fields = ['poNumber', 'totalCost', 'orderedBy', 'orderedAt', 'receivedAt']

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['orderedBy'] = request.user
            validated_data['orderedAt'] = timezone.now()

        purchase_order = PurchaseOrder.objects.create(**validated_data)

        for item_data in items_data:
            PurchaseOrderItem.objects.create(purchaseOrder=purchase_order, **item_data)

        purchase_order.totalCost = sum(item.lineTotal for item in purchase_order.items.all())
        purchase_order.save()
        return purchase_order

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)

        if instance.status != PurchaseOrder.POStatus.DRAFT and items_data is not None:
            raise serializers.ValidationError(
                'Cannot edit items on a non-draft purchase order.'
            )

        instance = super().update(instance, validated_data)

        if items_data is not None:
            instance.items.all().delete()
            for item_data in items_data:
                PurchaseOrderItem.objects.create(purchaseOrder=instance, **item_data)
            instance.totalCost = sum(item.lineTotal for item in instance.items.all())
            instance.save()

        return instance


class InventoryTransactionSerializer(serializers.ModelSerializer):
    inventoryItem = InventoryItemSerializer(read_only=True)
    inventoryItemId = serializers.PrimaryKeyRelatedField(
        queryset=InventoryItem.objects.all(), source='inventoryItem', write_only=True
    )
    relatedOrder = serializers.PrimaryKeyRelatedField(read_only=True)
    relatedPO = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = InventoryTransaction
        fields = [
            'transactionId',
            'inventoryItem',
            'inventoryItemId',
            'transactionType',
            'quantityChanged',
            'quantityBefore',
            'quantityAfter',
            'relatedOrder',
            'relatedPO',
            'note',
            'performedBy',
            'createdAt',
        ]
        read_only_fields = ['transactionId', 'quantityBefore', 'quantityAfter', 'performedBy', 'createdAt', 'status']
