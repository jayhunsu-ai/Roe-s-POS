from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SupplierViewSet,
    InventoryItemViewSet,
    PurchaseOrderViewSet,
    InventoryTransactionViewSet,
)

router = DefaultRouter()
router.register(r'suppliers', SupplierViewSet, basename='supplier')
router.register(r'items', InventoryItemViewSet, basename='inventoryitem')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchaseorder')
router.register(r'transactions', InventoryTransactionViewSet, basename='inventorytransaction')

app_name = 'inventory'

urlpatterns = [
    path('', include(router.urls)),
]
