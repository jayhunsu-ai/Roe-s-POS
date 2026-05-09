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

    id                    = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name                  = models.CharField(max_length=200)
    unit                  = models.CharField(max_length=10, choices=Unit.choices, default=Unit.UNITS)
    current_quantity      = models.FloatField(default=0)
    low_stock_threshold   = models.FloatField(default=0)
    default_usage_quantity = models.FloatField(default=0, help_text="Typical amount used per usage")
    note                  = models.TextField(blank=True)
    is_active             = models.BooleanField(default=True)
    created_at            = models.DateTimeField(auto_now_add=True)
    updated_at            = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'store_item'
        ordering = ['name']

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
