# menu/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, F
from django.db import transaction

from .models import Category, MenuItem, Stock, StockTransaction
from .serializers import (
    CategorySerializer, MenuItemSerializer, MenuItemListSerializer,
    StockSerializer, StockTransactionSerializer,
)
from accounts.permissions import IsAdmin, IsAdminOrReadOnly, IsAdminOrInventoryManager


class CategoryViewSet(viewsets.ModelViewSet):
    queryset           = Category.objects.all()
    serializer_class   = CategorySerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filterset_fields   = ['isActive']
    search_fields      = ['name']

    def get_queryset(self):
        qs         = Category.objects.all()
        # ── Bug Fix #11 (category): default false so admin sees all ───────
        active_only = self.request.query_params.get('active_only', 'false').lower() == 'true'
        if active_only:
            qs = qs.filter(isActive=True)
        return qs


class MenuItemViewSet(viewsets.ModelViewSet):
    queryset           = MenuItem.objects.all()
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filterset_fields   = ['category', 'itemType', 'isAvailable', 'trackStock']
    search_fields      = ['name', 'description']

    def get_serializer_class(self):
        if self.action == 'list':
            return MenuItemListSerializer
        return MenuItemSerializer

    def get_queryset(self):
        qs = MenuItem.objects.select_related('category', 'stock')

        # ── Bug Fix #11: default available_only to FALSE ─────────────────
        # Admin panel needs to list ALL items including unavailable ones.
        # POS client passes ?available_only=true explicitly.
        available_only = self.request.query_params.get('available_only', 'false').lower() == 'true'
        if available_only:
            qs = qs.filter(isAvailable=True).filter(
                Q(trackStock=False) | Q(trackStock=True, stock__quantity__gt=0)
            )
        return qs

    def _resolve_category(self, request):
        """
        Bug Fix #10 — original perform_create/perform_update mutated `data`
        but never passed the resolved category to serializer.save().
        Now returns the resolved Category instance (or None) so the view
        can pass it as extra kwargs to serializer.save().
        """
        category_raw = request.data.get('category')
        if category_raw and isinstance(category_raw, str):
            # Try treating it as a name first; if it looks like a UUID let DRF handle it
            try:
                import uuid as _uuid
                _uuid.UUID(str(category_raw))
                # It's a valid UUID — let the serializer resolve it normally
                return None
            except ValueError:
                # It's a plain name string — get or create the Category
                from .models import Category
                cat, _ = Category.objects.get_or_create(
                    name=category_raw,
                    defaults={'isActive': True}
                )
                return cat
        return None

    def perform_create(self, serializer):
        cat = self._resolve_category(self.request)
        if cat:
            serializer.save(category=cat)
        else:
            serializer.save()

    def perform_update(self, serializer):
        cat = self._resolve_category(self.request)
        if cat:
            serializer.save(category=cat)
        else:
            serializer.save()

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        categories = Category.objects.filter(isActive=True)
        result = []
        for category in categories:
            items = self.get_queryset().filter(category=category)
            if items.exists():
                result.append({
                    'category': CategorySerializer(category).data,
                    'items':    MenuItemListSerializer(items, many=True).data,
                })
        return Response(result)

    @action(detail=True, methods=['post'])
    def toggle_availability(self, request, pk=None):
        item = self.get_object()
        item.isAvailable = not item.isAvailable
        item.save(update_fields=['isAvailable', 'updatedAt'])
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=['get'])
    def stock_info(self, request, pk=None):
        item = self.get_object()
        if not item.trackStock:
            return Response({'message': 'This item does not track stock'})
        try:
            return Response(StockSerializer(item.stock).data)
        except Stock.DoesNotExist:
            return Response({'error': 'Stock not found'}, status=status.HTTP_404_NOT_FOUND)


class StockViewSet(viewsets.ModelViewSet):
    queryset           = Stock.objects.select_related('menuItem')
    serializer_class   = StockSerializer
    permission_classes = [IsAuthenticated, IsAdminOrInventoryManager]
    filterset_fields   = ['menuItem__isAvailable']
    search_fields      = ['menuItem__name']

    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'low_stock', 'out_of_stock']:
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        qs = self.get_queryset().filter(quantity__lt=F('lowStockThreshold'))
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=['get'])
    def out_of_stock(self, request):
        qs = self.get_queryset().filter(quantity=0)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=True, methods=['post'])
    def adjust_stock(self, request, pk=None):
        stock      = self.get_object()
        adjustment = request.data.get('adjustment', 0)
        note       = request.data.get('note', 'Manual adjustment')

        try:
            adjustment = int(adjustment)
        except (TypeError, ValueError):
            return Response({'error': 'Invalid adjustment value'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            stock          = Stock.objects.select_for_update().get(pk=stock.pk)
            before         = stock.quantity
            new_qty        = before + adjustment
            if new_qty < 0:
                return Response(
                    {'error': 'Adjustment would result in negative stock'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            stock.quantity = new_qty
            stock.save(update_fields=['quantity', 'updatedAt'])
            StockTransaction.objects.create(
                stock           = stock,
                transactionType = StockTransaction.TransactionType.ADJUSTMENT,
                quantityChanged = adjustment,
                quantityBefore  = before,
                quantityAfter   = stock.quantity,
                note            = note,
                performedBy     = request.user,
            )

        return Response({
            'message':      f'Stock adjusted by {adjustment}',
            'old_quantity': before,
            'new_quantity': stock.quantity,
            'stock':        self.get_serializer(stock).data,
        })

    @action(detail=True, methods=['post'])
    def restock(self, request, pk=None):
        stock    = self.get_object()
        quantity = request.data.get('quantity', 0)
        note     = request.data.get('note', 'Restock')

        try:
            quantity = int(quantity)
            assert quantity > 0
        except (TypeError, ValueError, AssertionError):
            return Response({'error': 'Quantity must be a positive integer'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            stock          = Stock.objects.select_for_update().get(pk=stock.pk)
            before         = stock.quantity
            stock.quantity += quantity
            stock.save(update_fields=['quantity', 'updatedAt'])
            StockTransaction.objects.create(
                stock           = stock,
                transactionType = StockTransaction.TransactionType.RESTOCK,
                quantityChanged = quantity,
                quantityBefore  = before,
                quantityAfter   = stock.quantity,
                note            = note,
                performedBy     = request.user,
            )

        return Response({
            'message':      f'Restocked {quantity} units',
            'old_quantity': before,
            'new_quantity': stock.quantity,
            'stock':        self.get_serializer(stock).data,
        })


class StockTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset           = StockTransaction.objects.select_related('stock__menuItem', 'performedBy')
    serializer_class   = StockTransactionSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filterset_fields   = ['transactionType', 'stock__menuItem', 'performedBy']
    search_fields      = ['stock__menuItem__name', 'note']