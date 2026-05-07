from django.contrib import admin
from .models import Supplier, InventoryItem, MenuItemIngredient, PurchaseOrder, PurchaseOrderItem, InventoryTransaction

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'contactName', 'phone', 'email', 'isActive']
    search_fields = ['name', 'contactName']

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'quantityInStock', 'unit', 'lowStockThreshold', 'isLowStock', 'costPerUnit']
    list_filter = ['unit', 'isActive']
    search_fields = ['name']

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ['poNumber', 'supplier', 'status', 'totalCost', 'createdAt']
    list_filter = ['status']

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = ['inventoryItem', 'transactionType', 'quantityChanged', 'quantityBefore', 'quantityAfter', 'createdAt']
    list_filter = ['transactionType']

admin.site.register(MenuItemIngredient)
admin.site.register(PurchaseOrderItem)