from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import StoreItem, StoreTransaction
from .serializers import (
    StoreItemSerializer,
    StoreItemListSerializer,
    StoreTransactionSerializer,
    StoreTransactionCreateSerializer,
)


class StoreItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    search_fields      = ['name', 'note']
    filterset_fields   = ['unit', 'is_active']

    def get_queryset(self):
        qs = StoreItem.objects.prefetch_related('transactions__recorded_by')
        active_only = self.request.query_params.get('active_only', 'true').lower() == 'true'
        if active_only:
            qs = qs.filter(is_active=True)
        return qs.order_by('name')

    def get_serializer_class(self):
        if self.action == 'list':
            return StoreItemListSerializer
        return StoreItemSerializer

    # ── POST /store/items/{id}/transact/ ─────────────────────────────────────
    @action(detail=True, methods=['post'])
    def transact(self, request, pk=None):
        """
        Log a stock movement against a store item.
        Body: { transaction_type, quantity, note }
        transaction_type: received | used | damaged | adjusted
        - received  → adds to current_quantity
        - used      → subtracts
        - damaged   → subtracts
        - adjusted  → sets absolute value (quantity = new total)
        """
        serializer = StoreTransactionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tx_type  = serializer.validated_data['transaction_type']
        quantity = serializer.validated_data['quantity']
        note     = serializer.validated_data.get('note', '')

        with transaction.atomic():
            item = StoreItem.objects.select_for_update().get(pk=pk)
            before = item.current_quantity

            if tx_type == StoreTransaction.TransactionType.RECEIVED:
                item.current_quantity += quantity
            elif tx_type in (
                StoreTransaction.TransactionType.USED,
                StoreTransaction.TransactionType.DAMAGED,
            ):
                item.current_quantity = max(0, item.current_quantity - quantity)
            elif tx_type == StoreTransaction.TransactionType.ADJUSTED:
                item.current_quantity = quantity  # treat as absolute override

            item.save()

            tx = StoreTransaction.objects.create(
                item=item,
                transaction_type=tx_type,
                quantity=quantity,
                quantity_before=before,
                quantity_after=item.current_quantity,
                note=note,
                recorded_by=request.user,
            )

        return Response(StoreTransactionSerializer(tx).data, status=status.HTTP_201_CREATED)

    # ── GET /store/items/low_stock/ ───────────────────────────────────────────
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        qs = self.get_queryset().filter(is_active=True)
        items = [i for i in qs if i.is_low_stock]
        serializer = StoreItemListSerializer(items, many=True)
        return Response(serializer.data)


class StoreTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only log of all store transactions"""
    permission_classes = [IsAuthenticated]
    serializer_class   = StoreTransactionSerializer
    filterset_fields   = ['transaction_type', 'item']

    def get_queryset(self):
        return StoreTransaction.objects.select_related(
            'item', 'recorded_by'
        ).order_by('-created_at')
