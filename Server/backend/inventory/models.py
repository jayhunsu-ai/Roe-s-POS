# inventory/models.py
from django.db import models, transaction
import uuid

class POCounter(models.Model):
    count = models.PositiveIntegerField(default=0)
    class Meta:
        db_table = 'po_counter'


class Supplier(models.Model):
    """Vendors/suppliers you purchase ingredients or stock from"""

    supplierId  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=200)
    contactName = models.CharField(max_length=200, blank=True)
    phone       = models.CharField(max_length=20, blank=True)
    email       = models.EmailField(blank=True)
    address     = models.TextField(blank=True)
    isActive    = models.BooleanField(default=True)
    createdAt   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'supplier'
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'

    def __str__(self):
        return self.name


class InventoryItem(models.Model):
    """
    Raw ingredients or supplies tracked in the kitchen/store.
    Separate from menu items — e.g. 'Tomatoes (kg)', 'Flour (bag)', 'Plastic Cups'
    """

    class Unit(models.TextChoices):
        KG        = 'kg', 'Kilograms'
        GRAMS     = 'g', 'Grams'
        LITRES    = 'L', 'Litres'
        ML        = 'ml', 'Millilitres'
        UNITS     = 'units', 'Units'
        BAGS      = 'bags', 'Bags'
        CARTONS   = 'cartons', 'Cartons'
        BOTTLES   = 'bottles', 'Bottles'
        PACKS     = 'packs', 'Packs'

    inventoryItemId   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name              = models.CharField(max_length=200)
    category          = models.CharField(max_length=100, blank=True, default='')
    description       = models.TextField(blank=True)
    unit              = models.CharField(max_length=10, choices=Unit.choices, default=Unit.UNITS)
    quantityInStock   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    lowStockThreshold = models.DecimalField(max_digits=10, decimal_places=2, default=5)
    costPerUnit       = models.FloatField(default=0.00)
    supplier          = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventoryItems'
    )
    isActive          = models.BooleanField(default=True)
    createdAt         = models.DateTimeField(auto_now_add=True)
    updatedAt         = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'inventory_item'
        verbose_name = 'Inventory Item'
        verbose_name_plural = 'Inventory Items'

    def __str__(self):
        return f"{self.name} ({self.quantityInStock} {self.unit})"

    @property
    def isLowStock(self):
        return self.quantityInStock < self.lowStockThreshold


class MenuItemIngredient(models.Model):
    """
    Links menu items to their raw ingredients.
    e.g. 'Jollof Rice' uses 200g of Rice, 50ml of Oil
    Enables auto-deduction of inventory when an order is placed.
    """

    ingredientId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    menuItem     = models.ForeignKey('menu.MenuItem', on_delete=models.CASCADE, related_name='ingredients')
    inventoryItem = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='usedIn')
    quantityUsed  = models.DecimalField(max_digits=10, decimal_places=3, help_text="Amount used per serving")

    class Meta:
        db_table = 'menu_item_ingredient'
        verbose_name = 'Menu Item Ingredient'
        verbose_name_plural = 'Menu Item Ingredients'
        unique_together = ('menuItem', 'inventoryItem')

    def __str__(self):
        return f"{self.menuItem.name} uses {self.quantityUsed} {self.inventoryItem.unit} of {self.inventoryItem.name}"


class PurchaseOrder(models.Model):
    """Records of stock purchased from suppliers"""

    class POStatus(models.TextChoices):
        DRAFT     = 'Draft', 'Draft'
        ORDERED   = 'Ordered', 'Ordered'
        RECEIVED  = 'Received', 'Received'
        CANCELLED = 'Cancelled', 'Cancelled'

    purchaseOrderId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    poNumber        = models.CharField(max_length=20, unique=True, editable=False)  # e.g. PO-0001
    supplier        = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, related_name='purchaseOrders')
    status          = models.CharField(max_length=15, choices=POStatus.choices, default=POStatus.DRAFT)
    totalCost       = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    note            = models.TextField(blank=True)
    orderedBy       = models.ForeignKey(
        'accounts.Staff', on_delete=models.SET_NULL, null=True, related_name='purchaseOrders'
    )
    orderedAt       = models.DateTimeField(null=True, blank=True)
    receivedAt      = models.DateTimeField(null=True, blank=True)
    createdAt       = models.DateTimeField(auto_now_add=True)
    updatedAt       = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'purchase_order'
        verbose_name = 'Purchase Order'
        verbose_name_plural = 'Purchase Orders'
        ordering = ['-createdAt']

    def __str__(self):
        return f"{self.poNumber} - {self.supplier} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.poNumber:
            with transaction.atomic():
                counter, _ = POCounter.objects.select_for_update().get_or_create(pk=1)
                counter.count += 1
                counter.save()
                self.poNumber = f"PO-{str(counter.count).zfill(4)}"
        super().save(*args, **kwargs)


class PurchaseOrderItem(models.Model):
    """Line items within a purchase order"""

    poItemId      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchaseOrder = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    inventoryItem = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name='purchaseItems')
    quantityOrdered   = models.DecimalField(max_digits=10, decimal_places=2)
    quantityReceived  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    costPerUnit       = models.DecimalField(max_digits=10, decimal_places=2)
    lineTotal         = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'purchase_order_item'
        verbose_name = 'Purchase Order Item'
        verbose_name_plural = 'Purchase Order Items'

    def __str__(self):
        return f"{self.inventoryItem.name} x{self.quantityOrdered} (PO: {self.purchaseOrder.poNumber})"

    def save(self, *args, **kwargs):
        self.lineTotal = self.costPerUnit * self.quantityOrdered
        super().save(*args, **kwargs)


class InventoryTransaction(models.Model):
    """Full audit log of every inventory movement"""

    class TransactionType(models.TextChoices):
        PURCHASE    = 'Purchase', 'Purchase'        # from purchase order
        USAGE       = 'Usage', 'Usage'              # deducted when order is made
        ADJUSTMENT  = 'Adjustment', 'Adjustment'    # manual correction
        WASTAGE     = 'Wastage', 'Wastage'          # spoilage/waste
        RETURN      = 'Return', 'Return'            # returned to supplier

    transactionId   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventoryItem   = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='transactions')
    transactionType = models.CharField(max_length=15, choices=TransactionType.choices)
    quantityChanged = models.DecimalField(max_digits=10, decimal_places=2, help_text="Positive = added, Negative = removed")
    quantityBefore  = models.DecimalField(max_digits=10, decimal_places=2)
    quantityAfter   = models.DecimalField(max_digits=10, decimal_places=2)
    relatedOrder    = models.ForeignKey(
        'orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='inventoryTransactions'
    )
    relatedPO       = models.ForeignKey(
        PurchaseOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='inventoryTransactions'
    )
    note            = models.TextField(blank=True)
    performedBy     = models.ForeignKey(
        'accounts.Staff', on_delete=models.SET_NULL, null=True, related_name='inventoryTransactions'
    )
    createdAt       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inventory_transaction'
        verbose_name = 'Inventory Transaction'
        verbose_name_plural = 'Inventory Transactions'
        ordering = ['-createdAt']

    def __str__(self):
        return f"{self.transactionType} | {self.inventoryItem.name} | {self.quantityChanged}"