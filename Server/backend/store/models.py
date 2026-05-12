from django.db import models
import uuid


class StoreItem(models.Model):
    class Unit(models.TextChoices):
        KG       = 'kg',      'Kilograms'
        GRAMS    = 'g',       'Grams'
        LITRES   = 'L',       'Litres'
        ML       = 'ml',      'Millilitres'
        UNITS    = 'units',   'Units'
        BAGS     = 'bags',    'Bags'
        CARTONS  = 'cartons', 'Cartons'
        BOTTLES  = 'bottles', 'Bottles'
        PACKS    = 'packs',   'Packs'
        CRATES   = 'crates',  'Crates'
        PIECES   = 'pieces',  'Pieces'

    class UsageUnit(models.TextChoices):
        CUPS         = 'cups',        'Cups'
        SCOOPS       = 'scoops',      'Scoops'
        ML           = 'ml',          'Millilitres'
        GRAMS        = 'g',           'Grams'
        PIECES       = 'pieces',      'Pieces'
        SERVINGS     = 'servings',    'Servings'
        LITRES       = 'L',           'Litres'
        TABLESPOONS  = 'tablespoons', 'Tablespoons'
        UNITS        = 'units',       'Units'

    id                     = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name                   = models.CharField(max_length=200)
    unit                   = models.CharField(max_length=10, choices=Unit.choices, default=Unit.UNITS)
    
    # How this item is measured when being consumed/used
    usage_unit             = models.CharField(
                                max_length=20,
                                choices=UsageUnit.choices,
                                default=UsageUnit.UNITS,
                                help_text="Unit used when consuming this item (e.g. cups, scoops)"
                             )
    # How many usage_units are in one stock unit
    # e.g. 1 bag of rice = 20 cups → units_per_item = 20
    units_per_item         = models.FloatField(
                                default=1.0,
                                help_text="How many usage units fit in one stock unit (e.g. 20 cups per bag)"
                             )
    
    current_quantity       = models.FloatField(default=0)
    low_stock_threshold    = models.FloatField(default=0)
    default_usage_quantity = models.FloatField(
                                default=0,
                                help_text="Default amount (in usage_unit) consumed per transaction"
                             )
    note                   = models.TextField(blank=True)
    is_active              = models.BooleanField(default=True)
    created_at             = models.DateTimeField(auto_now_add=True)
    updated_at             = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'store_item'
        ordering = ['name']

    def deduct(self, usage_qty: float):
        """Deduct usage_qty (in usage_unit) from current_quantity (in stock unit)."""
        if self.units_per_item <= 0:
            raise ValueError("units_per_item must be greater than 0")
        stock_deducted = usage_qty / self.units_per_item
        self.current_quantity = max(0, self.current_quantity - stock_deducted)
        self.save(update_fields=["current_quantity", "updated_at"])
        return stock_deducted

    def __str__(self):
        return f"{self.name} ({self.current_quantity} {self.unit})"

    @property
    def is_low_stock(self):
        return self.low_stock_threshold > 0 and self.current_quantity <= self.low_stock_threshold


class StoreTransaction(models.Model):
    class TransactionType(models.TextChoices):
        RECEIVED = 'received', 'Received'
        USED     = 'used',     'Used'
        DAMAGED  = 'damaged',  'Damaged'
        ADJUSTED = 'adjusted', 'Adjusted'

    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item             = models.ForeignKey(StoreItem, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    quantity         = models.FloatField(help_text="Always positive; direction determined by transaction_type")
    quantity_before  = models.FloatField()
    quantity_after   = models.FloatField()
    note             = models.CharField(max_length=300, blank=True)
    recorded_by      = models.ForeignKey(
        'accounts.Staff', on_delete=models.SET_NULL, null=True, related_name='store_transactions'
    )
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'store_transaction'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} | {self.item.name} | {self.quantity} {self.item.unit}"
