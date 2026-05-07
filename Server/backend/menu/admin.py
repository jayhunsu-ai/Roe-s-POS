from django.contrib import admin
from .models import Category, MenuItem, Stock, StockTransaction, MenuItemAddon
from inventory.models import MenuItemIngredient

class MenuItemIngredientInline(admin.TabularInline):
    model = MenuItemIngredient
    extra = 0
    fields = ['inventoryItem', 'quantity', 'unit']
    autocomplete_fields = ['inventoryItem']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'isActive', 'createdAt']
    search_fields = ['name']

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'itemType', 'price', 'isAvailable', 'trackStock']
    search_fields = ['name']
    list_filter = ['category', 'itemType', 'isAvailable']
    inlines = [MenuItemIngredientInline]

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['menuItem', 'quantity', 'unit', 'lowStockThreshold', 'isLowStock']

@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ['stock', 'transactionType', 'quantityChanged', 'quantityBefore', 'quantityAfter', 'createdAt']
    list_filter = ['transactionType']

@admin.register(MenuItemAddon)
class MenuItemAddonAdmin(admin.ModelAdmin):
    list_display = ['name', 'menuItem', 'extraPrice', 'isAvailable']