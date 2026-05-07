from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notification, NotificationPreference
from accounts.models import Staff


class NotificationService:
    """Service for creating and managing notifications"""

    @staticmethod
    def _emit_realtime(notification):
        """Push notification payload to websocket groups."""
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        payload = {
            'notificationId': str(notification.notificationId),
            'type': notification.type,
            'title': notification.title,
            'message': notification.message,
            'status': notification.status,
            'priority': notification.priority,
            'targetAdmin': str(notification.targetAdmin.staffId) if notification.targetAdmin else None,
            'createdAt': notification.createdAt.isoformat() if notification.createdAt else None,
        }

        try:
            async_to_sync(channel_layer.group_send)(
                'notifications_admin_all',
                {'type': 'notification_event', 'notification': payload},
            )
            if notification.targetAdmin:
                async_to_sync(channel_layer.group_send)(
                    f'notifications_admin_{notification.targetAdmin.staffId}',
                    {'type': 'notification_event', 'notification': payload},
                )
        except Exception:
            # Realtime delivery is best-effort: never break core flows
            # (orders/payments/etc.) if Redis/websocket layer is unavailable.
            return
    
    @staticmethod
    def create_low_stock_notification(inventory_item):
        """Create low stock alert notification"""
        admins = Staff.objects.filter(role=Staff.Roles.ADMIN)
        
        for admin in admins:
            # Check admin preferences
            try:
                prefs = admin.notification_preference
                if not prefs.notify_low_stock:
                    continue
            except NotificationPreference.DoesNotExist:
                pass
            
            title = f"Low Stock: {inventory_item.name}"
            message = (
                f"Stock for {inventory_item.name} is low. "
                f"Current: {inventory_item.quantityInStock} {inventory_item.unit}, "
                f"Threshold: {inventory_item.lowStockThreshold} {inventory_item.unit}"
            )
            
            notification = Notification.objects.create(
                type=Notification.NotificationType.LOW_STOCK,
                title=title,
                message=message,
                priority=3,
                inventoryItem=inventory_item,
                targetAdmin=admin
            )
            NotificationService._emit_realtime(notification)

    @staticmethod
    def create_out_of_stock_notification(inventory_item):
        """Create out of stock notification"""
        admins = Staff.objects.filter(role=Staff.Roles.ADMIN)
        
        for admin in admins:
            try:
                prefs = admin.notification_preference
                if not prefs.notify_out_of_stock:
                    continue
            except NotificationPreference.DoesNotExist:
                pass
            
            title = f"Out of Stock: {inventory_item.name}"
            message = f"{inventory_item.name} is now out of stock and needs immediate restocking."
            
            notification = Notification.objects.create(
                type=Notification.NotificationType.OUT_OF_STOCK,
                title=title,
                message=message,
                priority=5,  # Critical
                inventoryItem=inventory_item,
                targetAdmin=admin
            )
            NotificationService._emit_realtime(notification)

    @staticmethod
    def create_order_notification(order, notification_type):
        """Create order-related notification"""
        admins = Staff.objects.filter(role=Staff.Roles.ADMIN)
        customer = order.customerName or 'Walk-in Customer'
        balance = getattr(order, 'balance_due', None)
        balance_display = f"₦{float(balance):.2f}" if balance is not None else 'N/A'

        for admin in admins:
            try:
                prefs = admin.notification_preference
                if not prefs.notify_orders:
                    continue
            except NotificationPreference.DoesNotExist:
                pass

            if notification_type == Notification.NotificationType.ORDER_PLACED:
                title = f"New Order: {order.orderNumber}"
                message = (
                    f"Order {order.orderNumber} placed for {customer}. "
                    f"Total: ₦{float(order.totalAmount):.2f}. "
                    f"Balance due: {balance_display}."
                )
                priority = 2
            elif notification_type == Notification.NotificationType.ORDER_COMPLETED:
                title = f"Order Completed: {order.orderNumber}"
                message = f"Order {order.orderNumber} for {customer} has been completed and paid."
                priority = 1
            elif notification_type == Notification.NotificationType.ORDER_CANCELLED:
                title = f"Order Cancelled: {order.orderNumber}"
                message = f"Order {order.orderNumber} for {customer} has been cancelled."
                priority = 2
            elif notification_type == Notification.NotificationType.CREDIT_APPROVED:
                title = f"Credit Approved: {order.orderNumber}"
                message = (
                    f"Deferred payment approved for {customer}. "
                    f"Remaining balance: {balance_display}."
                )
                priority = 2
            else:
                return

            notification = Notification.objects.create(
                type=notification_type,
                title=title,
                message=message,
                priority=priority,
                order=order,
                targetAdmin=admin
            )
            NotificationService._emit_realtime(notification)

    @staticmethod
    def create_payment_notification(order, payment):
        """Create payment received notification"""
        from orders.models import Payment as OrderPayment

        admins = Staff.objects.filter(role=Staff.Roles.ADMIN)
        customer = order.customerName or 'Walk-in Customer'
        balance_display = f"₦{float(order.balance_due):.2f}"

        for admin in admins:
            try:
                prefs = admin.notification_preference
                if not prefs.notify_payments:
                    continue
            except NotificationPreference.DoesNotExist:
                pass

            if payment.method == OrderPayment.PaymentMethod.TRANSFER and payment.verificationStatus == OrderPayment.VerificationStatus.PENDING:
                title = f"Transfer Pending: {order.orderNumber}"
                message = (
                    f"Bank transfer of ₦{float(payment.amountPaid):.2f} recorded for {customer}. "
                    f"Ref: {payment.reference or 'N/A'}. Awaiting verification. "
                    f"Remaining balance: {balance_display}."
                )
                notification_type = Notification.NotificationType.PAYMENT_PENDING
            else:
                title = f"Payment Received: {order.orderNumber}"
                message = (
                    f"Payment of ₦{float(payment.amountPaid):.2f} received for {customer} "
                    f"via {payment.get_method_display()}. "
                    f"Remaining balance: {balance_display}."
                )
                notification_type = Notification.NotificationType.PAYMENT_RECEIVED

            notification = Notification.objects.create(
                type=notification_type,
                title=title,
                message=message,
                priority=2,
                order=order,
                targetAdmin=admin
            )
            NotificationService._emit_realtime(notification)

    @staticmethod
    def create_credit_notification(order, approver):
        """Create credit approval notification"""
        admins = Staff.objects.filter(role=Staff.Roles.ADMIN)
        customer = order.customerName or 'Walk-in Customer'
        balance_display = f"₦{float(order.balance_due):.2f}"

        for admin in admins:
            try:
                prefs = admin.notification_preference
                if not prefs.notify_orders:
                    continue
            except NotificationPreference.DoesNotExist:
                pass

            title = f"Credit Approved: {order.orderNumber}"
            message = (
                f"{approver.staffName} approved deferred payment for {customer}. "
                f"Remaining balance: {balance_display}."
            )

            notification = Notification.objects.create(
                type=Notification.NotificationType.CREDIT_APPROVED,
                title=title,
                message=message,
                priority=2,
                order=order,
                targetAdmin=admin
            )
            NotificationService._emit_realtime(notification)

    @staticmethod
    def create_system_notification(title, message, priority=1):
        """Create system error or info notification"""
        admins = Staff.objects.filter(role=Staff.Roles.ADMIN)
        
        for admin in admins:
            try:
                prefs = admin.notification_preference
                if not prefs.notify_system:
                    continue
            except NotificationPreference.DoesNotExist:
                pass
            
            notification = Notification.objects.create(
                type=Notification.NotificationType.SYSTEM_ERROR,
                title=title,
                message=message,
                priority=priority,
                targetAdmin=admin
            )
            NotificationService._emit_realtime(notification)
