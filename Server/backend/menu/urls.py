from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, MenuItemViewSet, StockViewSet, StockTransactionViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'items', MenuItemViewSet, basename='menuitem')
router.register(r'stock', StockViewSet, basename='stock')
router.register(r'stock-transactions', StockTransactionViewSet, basename='stocktransaction')

app_name = 'menu'

urlpatterns = [
    path('', include(router.urls)),
]
