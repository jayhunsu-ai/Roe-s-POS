from django.contrib import admin
from .models import Order, OrderItem, OrderItemAddon, Payment, Receipt


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'orderNumber', 'orderType', 'status', 'paymentStatus',
        'totalAmount', 'isCreditAllowed', 'creditApprovedBy', 'createdAt'
    ]
    list_filter = ['status', 'orderType', 'paymentStatus', 'isCreditAllowed']
    search_fields = ['orderNumber', 'customerName']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'menuItem', 'quantity', 'unitPrice', 'lineTotal']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'order', 'method', 'amountPaid', 'amountChange', 'verificationStatus', 'processedBy', 'createdAt'
    ]
    list_filter = ['method', 'verificationStatus']


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    list_display = ['receiptNumber', 'order', 'format', 'printCount', 'isDigitallySent', 'generatedAt']
    list_filter = ['format', 'isDigitallySent', 'generatedAt']
    search_fields = ['receiptNumber', 'order__orderNumber']
    readonly_fields = ['receiptId', 'receiptNumber', 'receiptContent', 'generatedAt', 'updatedAt']
    
    fieldsets = (
        ('Receipt Info', {'fields': ('receiptId', 'receiptNumber', 'order', 'format')}),
        ('Content', {
            'fields': ('receiptContent', 'receiptText', 'receiptHTML'),
            'classes': ('collapse',)
        }),
        ('Printing', {'fields': ('printedAt', 'printedBy', 'printCount')}),
        ('Digital', {'fields': ('isDigitallySent',)}),
        ('Timestamps', {'fields': ('generatedAt', 'updatedAt'), 'classes': ('collapse',)}),
    )
