from django.db import models
import uuid
from django.utils import timezone
from datetime import timedelta


class SalesSummary(models.Model):
    """Daily/weekly/monthly sales summaries"""

    class PeriodType(models.TextChoices):
        DAILY = 'Daily', 'Daily'
        WEEKLY = 'Weekly', 'Weekly'
        MONTHLY = 'Monthly', 'Monthly'

    summaryId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    periodType = models.CharField(max_length=10, choices=PeriodType.choices)
    startDate = models.DateField()
    endDate = models.DateField()

    # Sales metrics
    totalRevenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    totalOrders = models.PositiveIntegerField(default=0)
    averageOrderValue = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Item metrics
    totalItemsSold = models.PositiveIntegerField(default=0)
    uniqueItemsSold = models.PositiveIntegerField(default=0)

    # Payment metrics
    cashPayments = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    cardPayments = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    otherPayments = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    # Staff performance
    topStaff = models.JSONField(default=dict, help_text="Staff performance data")

    createdAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sales_summary'
        verbose_name = 'Sales Summary'
        verbose_name_plural = 'Sales Summaries'
        unique_together = ['periodType', 'startDate', 'endDate']
        ordering = ['-startDate']

    def __str__(self):
        return f"{self.periodType} Summary: {self.startDate} - {self.endDate}"


class ItemPerformance(models.Model):
    """Performance metrics for individual menu items"""

    performanceId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    menuItem = models.ForeignKey('menu.MenuItem', on_delete=models.CASCADE, related_name='performance')
    date = models.DateField()

    # Sales data
    quantitySold = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    orderCount = models.PositiveIntegerField(default=0)

    # Trends
    salesRank = models.PositiveIntegerField(default=0, help_text="Rank among all items that day")
    popularityScore = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    createdAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'item_performance'
        verbose_name = 'Item Performance'
        verbose_name_plural = 'Item Performance'
        unique_together = ['menuItem', 'date']
        ordering = ['-date', '-quantitySold']

    def __str__(self):
        return f"{self.menuItem.name} - {self.date}: {self.quantitySold} sold"


class HourlyAnalytics(models.Model):
    """Sales data broken down by hour"""

    analyticsId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateField()
    hour = models.PositiveIntegerField(help_text="Hour of day (0-23)")

    # Sales metrics
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    orderCount = models.PositiveIntegerField(default=0)
    averageOrderValue = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    # Item metrics
    itemsSold = models.PositiveIntegerField(default=0)
    popularItems = models.JSONField(default=list, help_text="Top 5 items sold this hour")

    createdAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'hourly_analytics'
        verbose_name = 'Hourly Analytics'
        verbose_name_plural = 'Hourly Analytics'
        unique_together = ['date', 'hour']
        ordering = ['-date', '-hour']

    def __str__(self):
        return f"{self.date} {self.hour:02d}:00 - ₦{self.revenue}"


class StaffPerformance(models.Model):
    """Performance metrics for staff members"""

    performanceId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    staff = models.ForeignKey('accounts.Staff', on_delete=models.CASCADE, related_name='performance')
    date = models.DateField()

    # Work metrics
    ordersTaken = models.PositiveIntegerField(default=0)
    ordersServed = models.PositiveIntegerField(default=0)
    totalRevenue = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Time metrics
    hoursWorked = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    averageOrderTime = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, help_text="Minutes per order")

    # Quality metrics
    customerSatisfaction = models.DecimalField(max_digits=3, decimal_places=1, default=0.0, help_text="1-5 rating")

    createdAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'staff_performance'
        verbose_name = 'Staff Performance'
        verbose_name_plural = 'Staff Performance'
        unique_together = ['staff', 'date']
        ordering = ['-date', '-totalRevenue']

    def __str__(self):
        return f"{self.staff.staffName} - {self.date}: ₦{self.totalRevenue}"


class InventoryAnalytics(models.Model):
    """Analytics for inventory management"""

    analyticsId = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventoryItem = models.ForeignKey('inventory.InventoryItem', on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField()

    # Stock metrics
    startingStock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    endingStock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stockUsed = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Cost metrics
    costOfGoodsSold = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    averageCostPerUnit = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    # Efficiency metrics
    stockTurnover = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="How many times stock was replaced")
    wastePercentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    createdAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inventory_analytics'
        verbose_name = 'Inventory Analytics'
        verbose_name_plural = 'Inventory Analytics'
        unique_together = ['inventoryItem', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.inventoryItem.name} - {self.date}: {self.stockUsed} used"
