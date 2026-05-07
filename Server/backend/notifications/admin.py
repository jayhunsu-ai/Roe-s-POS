from django.contrib import admin
from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['title', 'type', 'status', 'priority', 'createdAt', 'readAt']
    list_filter = ['type', 'status', 'priority', 'createdAt']
    search_fields = ['title', 'message']
    readonly_fields = ['notificationId', 'createdAt', 'readAt']
    ordering = ['-createdAt']
    
    fieldsets = (
        ('Notification Info', {'fields': ('notificationId', 'type', 'title', 'message')}),
        ('Status', {'fields': ('status', 'priority', 'readAt')}),
        ('Relations', {'fields': ('order', 'inventoryItem', 'menuItem', 'targetAdmin')}),
        ('Timestamps', {'fields': ('createdAt',), 'classes': ('collapse',)}),
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['staff', 'notify_low_stock', 'notify_out_of_stock', 'notify_orders', 'email_enabled']
    list_filter = ['notify_low_stock', 'notify_out_of_stock', 'notify_orders', 'email_enabled']
    search_fields = ['staff__staffName', 'staff__email']
    
    fieldsets = (
        ('Staff', {'fields': ('staff',)}),
        ('Notification Toggles', {
            'fields': ('notify_low_stock', 'notify_out_of_stock', 'notify_orders', 'notify_payments', 'notify_system')
        }),
        ('Email Settings', {
            'fields': ('email_enabled', 'email_low_stock'),
            'classes': ('collapse',)
        }),
        ('Thresholds', {'fields': ('low_stock_alert_days',)}),
    )

