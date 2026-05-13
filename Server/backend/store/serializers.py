from rest_framework import serializers
from .models import StoreItem, StoreTransaction


class StoreTransactionSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.SerializerMethodField()
    item_name        = serializers.CharField(source='item.name', read_only=True)
    item_unit        = serializers.CharField(source='item.unit', read_only=True)

    class Meta:
        model  = StoreTransaction
        fields = [
            'id', 'item', 'item_name', 'item_unit',
            'transaction_type', 'quantity',
            'quantity_before', 'quantity_after',
            'note', 'recorded_by', 'recorded_by_name', 'created_at',
        ]
        read_only_fields = ['id', 'quantity_before', 'quantity_after', 'recorded_by', 'created_at']

    def get_recorded_by_name(self, obj):
        if obj.recorded_by:
            return f"{obj.recorded_by.first_name} {obj.recorded_by.last_name}".strip()
        return None


class StoreItemSerializer(serializers.ModelSerializer):
    is_low_stock  = serializers.BooleanField(read_only=True)
    transactions  = StoreTransactionSerializer(many=True, read_only=True)

    class Meta:
        model  = StoreItem
        fields = [
            'id', 'name', 'unit', 'current_quantity',
            'low_stock_threshold', 'default_usage_quantity',
            'usage_unit', 'units_per_item',
            'note', 'is_active', 'is_low_stock',
            'created_at', 'updated_at', 'transactions',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class StoreItemListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — no nested transactions"""
    is_low_stock = serializers.BooleanField(read_only=True)

    class Meta:
        model  = StoreItem
        fields = [
            'id', 'name', 'unit', 'current_quantity',
            'low_stock_threshold', 'default_usage_quantity',
            'usage_unit', 'units_per_item',
            'note', 'is_active', 'is_low_stock',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'current_quantity', 'created_at', 'updated_at']


class StoreTransactionCreateSerializer(serializers.Serializer):
    """Used when the IM logs a transaction against a store item"""
    transaction_type = serializers.ChoiceField(choices=StoreTransaction.TransactionType.choices)
    quantity         = serializers.FloatField(min_value=0.0000001)
    note             = serializers.CharField(required=False, allow_blank=True, default='')
