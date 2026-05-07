from rest_framework import serializers
from .models import Category, MenuItem, Stock, StockTransaction
from inventory.models import MenuItemIngredient

class MenuItemIngredientSerializer(serializers.ModelSerializer):
    inventory_item_name = serializers.CharField(source='inventoryItem.name', read_only=True)
    unit = serializers.CharField(source='inventoryItem.unit', read_only=True)

    class Meta:
        model = MenuItemIngredient
        fields = ['ingredientId', 'inventoryItem', 'inventory_item_name', 'quantityUsed', 'unit']
        read_only_fields = ['ingredientId', 'inventory_item_name', 'unit']

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
    ingredients_count = serializers.SerializerMethodField()
    ingredients = MenuItemIngredientSerializer(many=True, required=False)

    class Meta:
        model = MenuItem
        fields = [
            'menuItemId', 'category', 'category_name', 'name', 'description',
            'itemType', 'price', 'image', 'isAvailable', 'trackStock',
            'createdAt', 'updatedAt', 'stock_info', 'ingredients_count', 'ingredients'
        ]
        read_only_fields = ['menuItemId', 'createdAt', 'updatedAt']

    def get_stock_info(self, obj):
        if not obj.trackStock:
            return None
        try:
            return {
                'quantity': obj.stock.quantity,
                'unit': obj.stock.unit,
            }
        except Stock.DoesNotExist:
            return None

    def get_ingredients_count(self, obj):
        return obj.ingredients.count()

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients', [])
        menu_item = MenuItem.objects.create(**validated_data)
        for ingredient_data in ingredients_data:
            MenuItemIngredient.objects.create(menuItem=menu_item, **ingredient_data)
        return menu_item

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if ingredients_data is not None:
            instance.ingredients.all().delete()
            for ingredient_data in ingredients_data:
                MenuItemIngredient.objects.create(menuItem=instance, **ingredient_data)
        return instance


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
