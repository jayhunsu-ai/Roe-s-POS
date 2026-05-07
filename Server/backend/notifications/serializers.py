from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationListSerializer(serializers.ModelSerializer):
    """Serializer for listing notifications"""
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'notificationId', 'type', 'type_display', 'title', 'message', 'status', 'status_display',
            'priority', 'createdAt', 'readAt'
        ]
        read_only_fields = ['notificationId', 'createdAt', 'readAt']


class NotificationDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed notification view"""
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    order_number = serializers.CharField(source='order.orderNumber', read_only=True, allow_null=True)
    
    class Meta:
        model = Notification
        fields = [
            'notificationId', 'type', 'type_display', 'title', 'message', 'status', 'status_display',
            'priority', 'order', 'order_number', 'inventoryItem', 'menuItem', 'createdAt', 'readAt'
        ]
        read_only_fields = ['notificationId', 'createdAt', 'readAt']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences"""
    staff_name = serializers.CharField(source='staff.staffName', read_only=True)
    
    class Meta:
        model = NotificationPreference
        fields = [
            'staff', 'staff_name', 'notify_low_stock', 'notify_out_of_stock',
            'notify_orders', 'notify_payments', 'notify_system', 'email_enabled',
            'email_low_stock', 'low_stock_alert_days', 'updatedAt'
        ]
        read_only_fields = ['staff', 'updatedAt']
