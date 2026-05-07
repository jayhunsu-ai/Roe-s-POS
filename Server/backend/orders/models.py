# orders/models.py
from django.db import models, transaction
from django.utils import timezone
from decimal import Decimal
import uuid


class OrderCounter(models.Model):
    count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'order_counter'
        verbose_name = 'Order Counter'
        verbose_name_plural = 'Order Counters'


class ReceiptCounter(models.Model):
    count = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'receipt_counter'
        verbose_name = 'Receipt Counter'
        verbose_name_plural = 'Receipt Counters'


class Order(models.Model):

    class OrderStatus(models.TextChoices):
        PENDING   = 'Pending',   'Pending'
        CONFIRMED = 'Confirmed', 'Confirmed'
        PREPARING = 'Preparing', 'Preparing'
        READY     = 'Ready',     'Ready'
        SERVED    = 'Served',    'Served'
        COMPLETED = 'Completed', 'Completed'
        CANCELLED = 'Cancelled', 'Cancelled'

    class OrderType(models.TextChoices):
        DINE_IN  = 'DineIn',   'Dine In'
        TAKEAWAY = 'Takeaway', 'Takeaway'
        DELIVERY = 'Delivery', 'Delivery'

    class PaymentStatus(models.TextChoices):
        UNPAID   = 'Unpaid',   'Unpaid'
        PAID     = 'Paid',     'Paid'
        PARTIAL  = 'Partial',  'Partial Payment'
        REFUNDED = 'Refunded', 'Refunded'

    class PaymentMethod(models.TextChoices):
        CASH         = 'Cash',        'Cash'
        CARD         = 'Card',        'Card'
        TRANSFER     = 'Transfer',    'Bank Transfer'
        MOBILE_MONEY = 'MobileMoney', 'Mobile Money'
        SPLIT        = 'Split',       'Split Payment'

    orderId       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    orderNumber   = models.CharField(max_length=20, unique=True, editable=False)
    orderType     = models.CharField(max_length=10, choices=OrderType.choices, default=OrderType.DINE_IN)
    status        = models.CharField(max_length=15, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    paymentStatus = models.CharField(max_length=10, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    paymentMethod = models.CharField(max_length=15, choices=PaymentMethod.choices, blank=True, null=True)
    tableNumber   = models.CharField(max_length=10, blank=True, null=True)
    customer      = models.ForeignKey(
        'Customer', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders'
    )
    customerName  = models.CharField(max_length=200, blank=True)
    customerPhone = models.CharField(max_length=20, blank=True)
    note          = models.TextField(blank=True)

    takenBy  = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, null=True, related_name='ordersTaken')
    servedBy = models.ForeignKey('accounts.Staff', on_delete=models.SET_NULL, null=True, blank=True, related_name='ordersServed')

    subtotal       = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discountAmount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    taxAmount      = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    totalAmount    = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    # ── BUG FIX #7: guard field prevents double inventory deduction ────────
    inventory_deducted = models.BooleanField(
        default=False,
        help_text="Set True after inventory has been deducted — prevents repeat deduction on re-save."
    )

    createdAt        = models.DateTimeField(auto_now_add=True)
    updatedAt        = models.DateTimeField(auto_now=True)
    completedAt      = models.DateTimeField(null=True, blank=True)
    isCreditAllowed  = models.BooleanField(default=False)
    creditApprovedBy = models.ForeignKey(
        'accounts.Staff', on_delete=models.SET_NULL, null=True, blank=True, related_name='creditsApproved'
    )
    creditApprovedAt = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'order'
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'
        ordering = ['-createdAt']

    def __str__(self):
        return f"{self.orderNumber} - {self.status}"

    def save(self, *args, **kwargs):
        if self.customer and not self.customerName:
            self.customerName = self.customer.name
        if self.customer and not self.customerPhone:
            self.customerPhone = self.customer.phone

        if self.pk:
            try:
                old = Order.objects.get(pk=self.pk)
                if old.status != self.status and self.status == Order.OrderStatus.COMPLETED:
                    self.completedAt = timezone.now()
            except Order.DoesNotExist:
                pass

        if not self.orderNumber:
            with transaction.atomic():
                counter, _ = OrderCounter.objects.select_for_update().get_or_create(pk=1)
                counter.count += 1
                counter.save()
                self.orderNumber = f"ORD-{str(counter.count).zfill(4)}"

        super().save(*args, **kwargs)

    def recalculate_totals(self):
        self.subtotal    = sum(item.lineTotal for item in self.items.all())
        discount         = Decimal(str(self.discountAmount))
        tax              = Decimal(str(self.taxAmount))
        self.totalAmount = self.subtotal - discount + tax
        self.save()

    @property
    def total_paid(self):
        return sum(
            (p.amountPaid for p in self.payments.all()),
            Decimal('0.00')
        )

    @property
    def verified_paid(self):
        return sum(
            (p.amountPaid for p in self.payments.filter(
                verificationStatus=Payment.VerificationStatus.CONFIRMED
            )),
            Decimal('0.00')
        )

    @property
    def balance_due(self):
        total = self.totalAmount
        if isinstance(total, float):
            total = Decimal(str(total))
        bal = total - self.total_paid
        return bal if bal > Decimal('0.00') else Decimal('0.00')

    @property
    def customer_display(self):
        return self.customerName or 'Walk-in Customer'

    def authorize_credit(self, approver):
        self.isCreditAllowed     = True
        self.creditApprovedBy    = approver
        self.creditApprovedAt    = timezone.now()
        self.save()


class OrderItem(models.Model):
    orderItemId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order       = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menuItem    = models.ForeignKey('menu.MenuItem', on_delete=models.SET_NULL, null=True, related_name='orderItems')
    menuItemName = models.CharField(max_length=200, blank=True)  # Denormalized for when menuItem is deleted
    quantity    = models.PositiveIntegerField(default=1)
    unitPrice   = models.DecimalField(max_digits=10, decimal_places=2)
    lineTotal   = models.DecimalField(max_digits=10, decimal_places=2)
    note        = models.TextField(blank=True)

    class Meta:
        db_table = 'order_item'

    def save(self, *args, **kwargs):
        if self.menuItem and not self.menuItemName:
            self.menuItemName = self.menuItem.name
        super().save(*args, **kwargs)

    def __str__(self):
        item_name = self.menuItem.name if self.menuItem else self.menuItemName
        return f"{self.quantity}x {item_name} (Order: {self.order.orderNumber})"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.unitPrice = self.menuItem.price
        self.lineTotal = Decimal(str(self.unitPrice)) * self.quantity
        super().save(*args, **kwargs)


class OrderItemAddon(models.Model):
    orderItemAddonId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    orderItem        = models.ForeignKey(OrderItem, on_delete=models.CASCADE, related_name='selectedAddons')
    addon            = models.ForeignKey('menu.MenuItemAddon', on_delete=models.PROTECT)
    extraPrice       = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        db_table = 'order_item_addon'

    def __str__(self):
        return f"{self.addon.name} for {self.orderItem.menuItem.name}"


class Payment(models.Model):

    class PaymentMethod(models.TextChoices):
        CASH         = 'Cash',        'Cash'
        CARD         = 'Card',        'Card'
        TRANSFER     = 'Transfer',    'Bank Transfer'
        MOBILE_MONEY = 'MobileMoney', 'Mobile Money'
        SPLIT        = 'Split',       'Split Payment'

    class VerificationStatus(models.TextChoices):
        PENDING   = 'Pending',   'Pending'
        CONFIRMED = 'Confirmed', 'Confirmed'
        REJECTED  = 'Rejected',  'Rejected'

    paymentId          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order              = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    method             = models.CharField(max_length=15, choices=PaymentMethod.choices)
    amountPaid         = models.DecimalField(max_digits=12, decimal_places=2)
    amountChange       = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    reference          = models.CharField(max_length=100, blank=True)
    verificationStatus = models.CharField(
        max_length=10, choices=VerificationStatus.choices,
        default=VerificationStatus.CONFIRMED
    )
    processedBy = models.ForeignKey(
        'accounts.Staff', on_delete=models.SET_NULL, null=True, related_name='paymentsProcessed'
    )
    createdAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'payment'

    def save(self, *args, **kwargs):
        if not self.pk and self.method == self.PaymentMethod.TRANSFER:
            self.verificationStatus = self.VerificationStatus.PENDING
        super().save(*args, **kwargs)

    @property
    def is_verified(self):
        return self.verificationStatus == self.VerificationStatus.CONFIRMED

    def __str__(self):
        return f"{self.method} - ₦{self.amountPaid} for {self.order.orderNumber}"


class Receipt(models.Model):

    class ReceiptFormat(models.TextChoices):
        THERMAL = 'Thermal', 'Thermal Printer (80mm)'
        A4      = 'A4',      'A4 Paper'
        MOBILE  = 'Mobile',  'Mobile/Digital'

    receiptId      = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order          = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='receipt')
    receiptNumber  = models.CharField(max_length=20, unique=True, editable=False)
    format         = models.CharField(max_length=10, choices=ReceiptFormat.choices, default=ReceiptFormat.THERMAL)
    receiptContent = models.JSONField(help_text="Structured receipt data")
    receiptHTML    = models.TextField(blank=True)
    receiptText    = models.TextField(blank=True)
    printedAt      = models.DateTimeField(null=True, blank=True)
    printedBy      = models.ForeignKey(
        'accounts.Staff', on_delete=models.SET_NULL, null=True, blank=True, related_name='receiptsPrinted'
    )
    printCount        = models.IntegerField(default=0)
    isDigitallySent   = models.BooleanField(default=False)
    generatedAt       = models.DateTimeField(auto_now_add=True)
    updatedAt         = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'receipt'
        ordering = ['-generatedAt']

    def __str__(self):
        return f"{self.receiptNumber} for {self.order.orderNumber}"

    def save(self, *args, **kwargs):
        if not self.receiptNumber:
            with transaction.atomic():
                counter, _ = ReceiptCounter.objects.select_for_update().get_or_create(pk=1)
                counter.count += 1
                counter.save()
                self.receiptNumber = f"REC-{str(counter.count).zfill(4)}"
        super().save(*args, **kwargs)


class Customer(models.Model):
    customerId  = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name        = models.CharField(max_length=200)
    phone       = models.CharField(max_length=20, blank=True)
    email       = models.EmailField(blank=True)
    isActive    = models.BooleanField(default=True)
    creditLimit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    createdAt   = models.DateTimeField(auto_now_add=True)
    updatedAt   = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'customer'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def outstanding_balance(self):
        return sum(
            (order.balance_due for order in self.orders.filter(
                paymentStatus__in=[Order.PaymentStatus.UNPAID, Order.PaymentStatus.PARTIAL]
            )),
            Decimal('0.00')
        )