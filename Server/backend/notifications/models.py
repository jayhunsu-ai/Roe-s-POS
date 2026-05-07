from django.db import models
import uuid


class Notification(models.Model):
    """Admin notifications for low stock, out of stock, order alerts, etc."""
    
    class NotificationType(models.TextChoices):
        LOW_STOCK = 'LowStock', 'Low Stock Alert'
        OUT_OF_STOCK = 'OutOfStock', 'Out Of Stock'
        ORDER_PLACED = 'OrderPlaced', 'Order Placed'
        ORDER_COMPLETED = 'OrderCompleted', 'Order Completed'
        ORDER_CANCELLED = 'OrderCancelled', 'Order Cancelled'
        PAYMENT_RECEIVED = 'PaymentReceived', 'Payment Received'
        PAYMENT_PENDING = 'PaymentPending', 'Payment Pending'
        CREDIT_APPROVED = 'CreditApproved', 'Credit Approved'
        SYSTEM_ERROR = 'SystemError', 'System Error'
    
    class NotificationStatus(models.TextChoices):
        UNREAD = 'Unread', 'Unread'
        READ = 'Read', 'Read'
        ARCHIVED = 'Archived', 'Archived'
    
    notificationId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    type = models.CharField(max_length=20, choices=NotificationType.choices)
    title = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=15, choices=NotificationStatus.choices, default=NotificationStatus.UNREAD)
    
    # Related objects (optional - can be null)
    order = models.ForeignKey(
        'orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications'
    )
    inventoryItem = models.ForeignKey(
        'inventory.InventoryItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications'
    )
    menuItem = models.ForeignKey(
        'menu.MenuItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='notifications'
    )
    
    # Admin targeting
    targetAdmin = models.ForeignKey(
        'accounts.Staff', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications'
    )
    
    # Metadata
    priority = models.IntegerField(default=1, help_text="1=Low, 5=Critical")
    createdAt = models.DateTimeField(auto_now_add=True)
    readAt = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'notification'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-createdAt']
        indexes = [
            models.Index(fields=['-createdAt']),
            models.Index(fields=['status']),
            models.Index(fields=['type']),
        ]

    def __str__(self):
        return f"{self.get_type_display()} - {self.title}"

    def mark_as_read(self):
        """Mark notification as read"""
        from django.utils import timezone
        self.status = self.NotificationStatus.READ
        self.readAt = timezone.now()
        self.save()


class NotificationPreference(models.Model):
    """Admin notification preferences"""
    
    staff = models.OneToOneField('accounts.Staff', on_delete=models.CASCADE, related_name='notification_preference')
    
    # Toggle notifications by type
    notify_low_stock = models.BooleanField(default=True)
    notify_out_of_stock = models.BooleanField(default=True)
    notify_orders = models.BooleanField(default=True)
    notify_payments = models.BooleanField(default=True)
    notify_system = models.BooleanField(default=True)
    
    # Email notifications
    email_enabled = models.BooleanField(default=False)
    email_low_stock = models.BooleanField(default=False)
    
    # Thresholds
    low_stock_alert_days = models.IntegerField(default=1, help_text="Alert when stock will last this many days")
    
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notification_preference'
        verbose_name = 'Notification Preference'
        verbose_name_plural = 'Notification Preferences'

    def __str__(self):
        return f"Preferences for {self.staff.staffName}"
