from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncDate, TruncHour, ExtractHour
from django.utils import timezone
from datetime import datetime, timedelta
from .models import SalesSummary, ItemPerformance, HourlyAnalytics, StaffPerformance, InventoryAnalytics
from .serializers import (
    SalesSummarySerializer, ItemPerformanceSerializer, HourlyAnalyticsSerializer,
    StaffPerformanceSerializer, InventoryAnalyticsSerializer
)
from accounts.permissions import IsAdmin
from django.db.models import F


class AnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """Main analytics dashboard viewset"""
    permission_classes = [IsAuthenticated, IsAdmin]

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get comprehensive dashboard data"""
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        this_week_start = today - timedelta(days=today.weekday())
        this_month_start = today.replace(day=1)

        # Today's metrics
        today_orders = self._get_orders_for_date(today)
        yesterday_orders = self._get_orders_for_date(yesterday)

        # Revenue comparison
        today_revenue = today_orders.aggregate(total=Sum('totalAmount'))['total'] or 0
        yesterday_revenue = yesterday_orders.aggregate(total=Sum('totalAmount'))['total'] or 0
        revenue_change = self._calculate_percentage_change(today_revenue, yesterday_revenue)

        # Order count comparison
        today_count = today_orders.count()
        yesterday_count = yesterday_orders.count()
        order_change = self._calculate_percentage_change(today_count, yesterday_count)

        # Top items today (by sales volume)
        top_items = self._get_top_items(today, limit=5)
        
        # Highest priced items
        highest_priced_items = self._get_highest_priced_items(limit=5)

        # Hourly breakdown
        hourly_data = self._get_hourly_revenue(today)

        # Low stock alerts
        low_stock_items = self._get_low_stock_items()

        return Response({
            'summary': {
                'today_revenue': float(today_revenue),
                'yesterday_revenue': float(yesterday_revenue),
                'revenue_change': revenue_change,
                'today_orders': today_count,
                'yesterday_orders': yesterday_count,
                'order_change': order_change,
                'average_order_value': float(today_revenue / today_count) if today_count > 0 else 0,
            },
            'top_items': top_items,
            'highest_priced_items': highest_priced_items,
            'hourly_revenue': hourly_data,
            'alerts': {
                'low_stock': low_stock_items,
                'pending_orders': self._get_pending_orders_count(),
            }
        })

    @action(detail=False, methods=['get'])
    def sales_report(self, request):
        """Generate sales report for date range"""
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        period = request.query_params.get('period', 'daily')  # daily, weekly, monthly

        if not start_date or not end_date:
            return Response(
                {'error': 'start_date and end_date are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            start = datetime.fromisoformat(start_date).date()
            end = datetime.fromisoformat(end_date).date()
        except ValueError:
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get orders in date range
        orders = self._get_orders_for_date_range(start, end)

        # Aggregate data
        total_revenue = orders.aggregate(total=Sum('totalAmount'))['total'] or 0
        total_orders = orders.count()
        avg_order_value = float(total_revenue / total_orders) if total_orders > 0 else 0

        # Payment method breakdown
        payment_breakdown = orders.values('payments__method').annotate(
            total=Sum('payments__amountPaid')
        ).order_by('-total')

        # Top selling items
        top_items = self._get_top_items_in_range(start, end, limit=10)

        # Daily breakdown
        daily_breakdown = []
        current_date = start
        while current_date <= end:
            day_orders = orders.filter(createdAt__date=current_date)
            day_revenue = day_orders.aggregate(total=Sum('totalAmount'))['total'] or 0
            daily_breakdown.append({
                'date': current_date.isoformat(),
                'revenue': float(day_revenue),
                'orders': day_orders.count(),
                'avg_order': float(day_revenue / day_orders.count()) if day_orders.count() > 0 else 0
            })
            current_date += timedelta(days=1)

        return Response({
            'period': {'start': start.isoformat(), 'end': end.isoformat()},
            'summary': {
                'total_revenue': float(total_revenue),
                'total_orders': total_orders,
                'average_order_value': avg_order_value,
                'total_days': (end - start).days + 1,
            },
            'payment_methods': list(payment_breakdown),
            'top_items': top_items,
            'daily_breakdown': daily_breakdown,
        })

    @action(detail=False, methods=['get'])
    def item_performance(self, request):
        """Get item performance analytics"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)

        # Get item performance data
        performances = ItemPerformance.objects.filter(
            date__gte=start_date
        ).select_related('menuItem').order_by('-revenue')[:20]

        # Group by item with aggregated data
        item_stats = {}
        for perf in performances:
            item_id = str(perf.menuItem.menuItemId)
            if item_id not in item_stats:
                item_stats[item_id] = {
                    'item_id': item_id,
                    'item_name': perf.menuItem.name,
                    'total_sold': 0,
                    'total_revenue': 0,
                    'avg_daily_sales': 0,
                    'days_with_sales': 0,
                }
            item_stats[item_id]['total_sold'] += perf.quantitySold
            item_stats[item_id]['total_revenue'] += float(perf.revenue)
            if perf.quantitySold > 0:
                item_stats[item_id]['days_with_sales'] += 1

        # Calculate averages
        for stats in item_stats.values():
            stats['avg_daily_sales'] = stats['total_sold'] / days if days > 0 else 0

        return Response({
            'period_days': days,
            'items': list(item_stats.values())
        })

    @action(detail=False, methods=['get'])
    def peak_hours(self, request):
        """Analyze peak business hours"""
        days = int(request.query_params.get('days', 7))
        start_date = timezone.now().date() - timedelta(days=days)

        # Get hourly data
        hourly_data = HourlyAnalytics.objects.filter(
            date__gte=start_date
        ).values('hour').annotate(
            avg_revenue=Avg('revenue'),
            avg_orders=Avg('orderCount'),
            total_revenue=Sum('revenue'),
            total_orders=Sum('orderCount')
        ).order_by('hour')

        # Find peak hours
        peak_revenue_hour = max(hourly_data, key=lambda x: x['avg_revenue']) if hourly_data else None
        peak_orders_hour = max(hourly_data, key=lambda x: x['avg_orders']) if hourly_data else None

        return Response({
            'period_days': days,
            'hourly_breakdown': list(hourly_data),
            'peak_hours': {
                'revenue_peak': peak_revenue_hour,
                'orders_peak': peak_orders_hour,
            }
        })

    @action(detail=False, methods=['get'])
    def staff_performance(self, request):
        """Get staff performance metrics"""
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now().date() - timedelta(days=days)

        # Get staff performance data
        performances = StaffPerformance.objects.filter(
            date__gte=start_date
        ).select_related('staff').order_by('-totalRevenue')

        staff_stats = {}
        for perf in performances:
            staff_id = str(perf.staff.staffId)
            if staff_id not in staff_stats:
                staff_stats[staff_id] = {
                    'staff_id': staff_id,
                    'staff_name': perf.staff.staffName,
                    'role': perf.staff.role,
                    'total_orders': 0,
                    'total_revenue': 0,
                    'avg_order_time': 0,
                    'working_days': 0,
                }
            staff_stats[staff_id]['total_orders'] += perf.ordersTaken
            staff_stats[staff_id]['total_revenue'] += float(perf.totalRevenue)
            staff_stats[staff_id]['working_days'] += 1

        # Calculate averages
        for stats in staff_stats.values():
            stats['avg_daily_orders'] = stats['total_orders'] / stats['working_days'] if stats['working_days'] > 0 else 0
            stats['avg_daily_revenue'] = stats['total_revenue'] / stats['working_days'] if stats['working_days'] > 0 else 0

        return Response({
            'period_days': days,
            'staff': list(staff_stats.values())
        })

    # Helper methods
    def _get_orders_for_date(self, date):
        """Get orders for a specific date"""
        from orders.models import Order
        return Order.objects.filter(
            createdAt__date=date
            # Removed status filter to show all orders
        )

    def _get_orders_for_date_range(self, start_date, end_date):
        """Get orders for a date range"""
        from orders.models import Order
        return Order.objects.filter(
            createdAt__date__gte=start_date,
            createdAt__date__lte=end_date
            # Removed status filter to show all orders
        )

    def _calculate_percentage_change(self, current, previous):
        """Calculate percentage change"""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round(((current - previous) / previous) * 100, 2)

    def _get_top_items(self, date, limit=5):
        """Get top selling items for a date"""
        from orders.models import OrderItem
        return list(OrderItem.objects.filter(
            order__createdAt__date=date
        ).values('menuItem__name').annotate(
            total_sold=Sum('quantity'),
            revenue=Sum('lineTotal')
        ).order_by('-total_sold')[:limit])

    def _get_top_items_in_range(self, start_date, end_date, limit=10):
        """Get top selling items for date range"""
        from orders.models import OrderItem
        return list(OrderItem.objects.filter(
            order__createdAt__date__gte=start_date,
            order__createdAt__date__lte=end_date
        ).values('menuItem__name').annotate(
            total_sold=Sum('quantity'),
            revenue=Sum('lineTotal')
        ).order_by('-total_sold')[:limit])

    def _get_hourly_revenue(self, date):
        """Get hourly revenue breakdown"""
        from orders.models import Order
        hourly_data = Order.objects.filter(
            createdAt__date=date,
            status__in=['Completed', 'Paid']
        ).annotate(
            hour=ExtractHour('createdAt')
        ).values('hour').annotate(
            revenue=Sum('totalAmount'),
            orders=Count('orderId')
        ).order_by('hour')

        # Fill missing hours with zeros
        result = []
        for hour in range(24):
            hour_data = next((h for h in hourly_data if h['hour'] == hour), None)
            result.append({
                'hour': hour,
                'revenue': float(hour_data['revenue']) if hour_data else 0,
                'orders': hour_data['orders'] if hour_data else 0
            })
        return result

    def _get_low_stock_items(self):
        """Get low stock inventory items"""
        from inventory.models import InventoryItem
        return list(
            InventoryItem.objects.filter(
                quantityInStock__lte=F('lowStockThreshold')
            ).values('name', 'quantityInStock', 'lowStockThreshold')[:5]
        )

    def _get_pending_orders_count(self):
        """Get count of pending orders"""
        from orders.models import Order
        return Order.objects.filter(
            status__in=['Pending', 'Confirmed', 'Preparing']
        ).count()
