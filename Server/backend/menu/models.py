from django.db import models
import uuid


class Category(models.Model):
    """Food/drink categories e.g. Drinks, Snacks, Main Course"""

    categoryId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    isActive = models.BooleanField(default=True)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'category'
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    """Individual items on the menu"""

    class ItemType(models.TextChoices):
        FOOD = 'Food', 'Food'
        DRINK = 'Drink', 'Drink'
        COMBO = 'Combo', 'Combo'
        OTHER = 'Other', 'Other'

    menuItemId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='menuItems')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    itemType = models.CharField(max_length=10, choices=ItemType.choices, default=ItemType.FOOD)
    price = models.FloatField(default=0.00)
    image = models.ImageField(upload_to='menu_images/', blank=True, null=True)
    isAvailable = models.BooleanField(default=True)  # toggle on/off from POS
    trackStock = models.BooleanField(default=False)  # whether to track stock for this item
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'menu_item'
        verbose_name = 'Menu Item'
        verbose_name_plural = 'Menu Items'

    def __str__(self):
        from django.conf import settings
        currency_symbol = getattr(settings, 'CURRENCY_SYMBOL', '₦')
        return f"{self.name} - {currency_symbol}{self.price}"

    @property
    def isInStock(self):
        """Returns True if item is in stock or doesn't track stock"""
        if not self.trackStock:
            return True
        try:
            return self.stock.quantity > 0
        except Stock.DoesNotExist:
            return False


class Stock(models.Model):
    """Tracks inventory quantity for menu items that need stock management"""

    stockId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    menuItem = models.OneToOneField(MenuItem, on_delete=models.CASCADE, related_name='stock')
    quantity = models.PositiveIntegerField(default=0)
    lowStockThreshold = models.PositiveIntegerField(default=10, help_text="Alert when stock falls below this")
    unit = models.CharField(max_length=50, default='units', help_text="e.g. units, kg, litres, plates")
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'stock'
        verbose_name = 'Stock'
        verbose_name_plural = 'Stock'

    def __str__(self):
        return f"{self.menuItem.name} - {self.quantity} {self.unit}"

    @property
    def isLowStock(self):
        return self.quantity < self.lowStockThreshold


class StockTransaction(models.Model):
    """Logs every stock movement — restocks, sales deductions, adjustments"""

    class TransactionType(models.TextChoices):
        RESTOCK = 'Restock', 'Restock'
        SALE = 'Sale', 'Sale'
        ADJUSTMENT = 'Adjustment', 'Manual Adjustment'
        WASTAGE = 'Wastage', 'Wastage'

    transactionId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name='transactions')
    transactionType = models.CharField(max_length=15, choices=TransactionType.choices)
    quantityChanged = models.IntegerField(help_text="Positive for additions, negative for deductions")
    quantityBefore = models.PositiveIntegerField()
    quantityAfter = models.PositiveIntegerField()
    note = models.TextField(blank=True)
    # 'accounts.Staff' refers to the Staff model in the accounts app
    performedBy = models.ForeignKey(
        'accounts.Staff', on_delete=models.SET_NULL, null=True, related_name='stockTransactions'
    )
    createdAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'stock_transaction'
        verbose_name = 'Stock Transaction'
        verbose_name_plural = 'Stock Transactions'
        ordering = ['-createdAt']

    def __str__(self):
        return f"{self.transactionType} | {self.stock.menuItem.name} | {self.quantityChanged}"


class MenuItemAddon(models.Model):
    """Optional add-ons for menu items e.g. extra sauce, extra cheese"""

    addonId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    menuItem = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='addons')
    name = models.CharField(max_length=100)
    extraPrice = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    isAvailable = models.BooleanField(default=True)

    class Meta:
        db_table = 'menu_item_addon'
        verbose_name = 'Menu Item Addon'

    def __str__(self):
        from django.conf import settings
        currency_symbol = getattr(settings, 'CURRENCY_SYMBOL', '₦')
        return f"{self.name} (+{currency_symbol}{self.extraPrice}) for {self.menuItem.name}"