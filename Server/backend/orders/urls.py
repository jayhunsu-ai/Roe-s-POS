from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReceiptViewSet, OrderViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r'receipts', ReceiptViewSet, basename='receipt')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'payments', PaymentViewSet, basename='payment')

app_name = 'orders'

urlpatterns = [
    path('', include(router.urls)),
]
