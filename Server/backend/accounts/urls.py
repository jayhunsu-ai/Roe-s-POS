from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StaffViewSet

router = DefaultRouter()
router.register(r'staff', StaffViewSet, basename='staff')

app_name = 'accounts'

urlpatterns = [
    path('', include(router.urls)),
]
