from rest_framework import serializers
from .models import Category, MenuItem, Stock, StockTransaction
from inventory.models import MenuItemIngredient

class MenuItemIngredientSerializer(serializers.ModelSerializer):
    inventory_item_name = serializers.CharField(source='inventoryItem.name', read_only=True)
    unit = serializers.CharField(source='inventoryItem.unit', read_only=True)

    class Meta:
        model = MenuItemIngredient
        fields = ['id', 'inventoryItem', 'inventory_item_name', 'quantity', 'unit']
        read_only_fields = ['id']

class CategorySerializer(serializers.ModelSerializer):
    """Serializer for menu categories"""
    menu_items_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'categoryId', 'name', 'description', 'isActive',
            'createdAt', 'updatedAt', 'menu_items_count'
        ]
        read_only_fields = ['categoryId', 'createdAt', 'updatedAt']

    def get_menu_items_count(self, obj):
        return obj.menuItems.filter(isAvailable=True).count()


class MenuItemListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing menu items"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_in_stock = serializers.BooleanField(source='isInStock', read_only=True)
    stock_quantity = serializers.SerializerMethodField()

    class Meta:
        model = MenuItem
        fields = [
            'menuItemId', 'name', 'price', 'itemType', 'category_name',
            'isAvailable', 'is_in_stock', 'trackStock', 'stock_quantity', 'image'
        ]

    def get_stock_quantity(self, obj):
        if obj.trackStock and hasattr(obj, 'stock'):
            return obj.stock.quantity
        return None


class MenuItemSerializer(serializers.ModelSerializer):
    """Full serializer for menu item details"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    stock_info = serializers.SerializerMethodField()
    ingredients = MenuItemIngredientSerializer(many=True, read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            'menuItemId', 'category', 'category_name', 'name', 'description',
            'itemType', 'price', 'image', 'isAvailable', 'trackStock',
            'createdAt', 'updatedAt', 'stock_info', 'ingredients'
        ]
        read_only_fields = ['menuItemId', 'createdAt', 'updatedAt']


class StockSerializer(serializers.ModelSerializer):
    """Serializer for stock information"""
    menu_item_name = serializers.CharField(source='menuItem.name', read_only=True)
    is_low_stock = serializers.BooleanField(source='isLowStock', read_only=True)

    class Meta:
        model = Stock
        fields = [
            'stockId', 'menuItem', 'menu_item_name', 'quantity',
            'lowStockThreshold', 'unit', 'is_low_stock', 'updatedAt'
        ]
        read_only_fields = ['stockId', 'updatedAt']


class StockTransactionSerializer(serializers.ModelSerializer):
    """Serializer for stock transaction history"""
    menu_item_name = serializers.CharField(source='stock.menuItem.name', read_only=True)
    performed_by_name = serializers.CharField(source='performedBy.staffName', read_only=True)

    class Meta:
        model = StockTransaction
        fields = [
            'transactionId', 'stock', 'menu_item_name', 'transactionType',
            'quantityChanged', 'quantityBefore', 'quantityAfter', 'note',
            'performedBy', 'performed_by_name', 'createdAt'
        ]
        read_only_fields = ['transactionId', 'createdAt']
