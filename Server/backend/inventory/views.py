from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import F
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as filters

from .models import (
    Supplier,
    InventoryItem,
    PurchaseOrder,
    InventoryTransaction,
)
from .serializers import (
    SupplierSerializer,
    InventoryItemSerializer,
    PurchaseOrderSerializer,
    InventoryTransactionSerializer,
)
from accounts.permissions import IsAuthenticatedAndInventoryManagerOrReadOnly


class InventoryTransactionFilter(filters.FilterSet):
    transactionType = filters.CharFilter(method='filter_transaction_type')

    def filter_transaction_type(self, queryset, name, value):
        return queryset.filter(transactionType__iexact=value)

    class Meta:
        model = InventoryTransaction
        fields = ['transactionType', 'inventoryItem', 'performedBy', 'relatedPO']


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticatedAndInventoryManagerOrReadOnly]
    filterset_fields = ['isActive']
    search_fields = ['name', 'contactName', 'phone', 'email']

    def get_queryset(self):
        queryset = Supplier.objects.all()
        active_only = self.request.query_params.get('active_only', 'true').lower() == 'true'
        if active_only:
            queryset = queryset.filter(isActive=True)
        return queryset


class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.select_related('supplier').all()
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticatedAndInventoryManagerOrReadOnly]
    filterset_fields = ['supplier', 'unit', 'isActive']
    search_fields = ['name', 'description']

    def get_queryset(self):
        queryset = InventoryItem.objects.select_related('supplier')
        active_only = self.request.query_params.get('active_only', 'true').lower() == 'true'
        if active_only:
            queryset = queryset.filter(isActive=True)
        return queryset

    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        queryset = self.get_queryset().filter(quantityInStock__lte=F('lowStockThreshold'))
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def out_of_stock(self, request):
        queryset = self.get_queryset().filter(quantityInStock__lte=0)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = PurchaseOrder.objects.select_related('supplier', 'orderedBy').prefetch_related('items__inventoryItem')
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated, IsAuthenticatedAndInventoryManagerOrReadOnly]
    filterset_fields = ['status', 'supplier', 'orderedBy']
    search_fields = ['poNumber', 'supplier__name', 'note']

    def perform_create(self, serializer):
        serializer.save(orderedBy=self.request.user)

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        with transaction.atomic():
            # Lock the row immediately so concurrent requests cannot double-receive
            purchase_order = PurchaseOrder.objects.select_for_update().get(pk=pk)

            if purchase_order.status == PurchaseOrder.POStatus.RECEIVED:
                return Response(
                    {'detail': 'Purchase order has already been received.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            purchase_order.status = PurchaseOrder.POStatus.RECEIVED
            purchase_order.receivedAt = timezone.now()
            purchase_order.save()

            for item in purchase_order.items.all():
                received_quantity = (
                    item.quantityReceived if item.quantityReceived > 0
                    else item.quantityOrdered
                )

                inventory_item = InventoryItem.objects.select_for_update().get(
                    pk=item.inventoryItem.pk
                )
                before = inventory_item.quantityInStock
                inventory_item.quantityInStock += received_quantity
                inventory_item.save()

                InventoryTransaction.objects.create(
                    inventoryItem=inventory_item,
                    transactionType=InventoryTransaction.TransactionType.PURCHASE,
                    quantityChanged=received_quantity,
                    quantityBefore=before,
                    quantityAfter=inventory_item.quantityInStock,
                    relatedPO=purchase_order,
                    note=f"Received {received_quantity} {inventory_item.unit} from PO {purchase_order.poNumber}",
                    performedBy=request.user,
                )

        purchase_order.refresh_from_db()
        return Response(self.get_serializer(purchase_order).data)

    def update(self, request, *args, **kwargs):
        po = self.get_object()

        if po.status != PurchaseOrder.POStatus.DRAFT:
            if 'items' in request.data:
                return Response(
                    {'detail': 'Cannot edit items on a non-draft purchase order.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if any(k in request.data for k in ['supplier', 'status']):
                return Response(
                    {'detail': 'Purchase order is locked'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        # PATCH always routes through update so the guard runs
        return self.update(request, *args, **kwargs)


class InventoryTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = InventoryTransaction.objects.select_related('inventoryItem', 'performedBy', 'relatedPO')
    serializer_class = InventoryTransactionSerializer
    permission_classes = [IsAuthenticatedAndInventoryManagerOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = InventoryTransactionFilter
    search_fields = ['inventoryItem__name', 'note']
