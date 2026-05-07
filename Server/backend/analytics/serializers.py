from rest_framework import serializers
from .models import SalesSummary, ItemPerformance, HourlyAnalytics, StaffPerformance, InventoryAnalytics


class SalesSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesSummary
        fields = '__all__'
        read_only_fields = ['summaryId', 'createdAt']


class ItemPerformanceSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='menuItem.name', read_only=True)
    category = serializers.SerializerMethodField()

    class Meta:
        model = ItemPerformance
        fields = '__all__'
        read_only_fields = ['performanceId', 'createdAt']

    def get_category(self, obj):
        return obj.menuItem.category.name if obj.menuItem.category else None


class HourlyAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = HourlyAnalytics
        fields = '__all__'
        read_only_fields = ['analyticsId', 'createdAt']


class StaffPerformanceSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.staffName', read_only=True)
    staff_role = serializers.CharField(source='staff.role', read_only=True)

    class Meta:
        model = StaffPerformance
        fields = '__all__'
        read_only_fields = ['performanceId', 'createdAt']


class InventoryAnalyticsSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='inventoryItem.name', read_only=True)
    current_stock = serializers.DecimalField(
        source='inventoryItem.quantityInStock',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = InventoryAnalytics
        fields = '__all__'
        read_only_fields = ['analyticsId', 'createdAt']
