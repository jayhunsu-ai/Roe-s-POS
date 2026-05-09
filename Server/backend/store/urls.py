from rest_framework.routers import DefaultRouter
from .views import StoreItemViewSet, StoreTransactionViewSet

router = DefaultRouter()
router.register(r'items',        StoreItemViewSet,        basename='store-item')
router.register(r'transactions', StoreTransactionViewSet, basename='store-transaction')

urlpatterns = router.urls
