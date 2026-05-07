from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, NotificationPreferenceViewSet

router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')

app_name = 'notifications'

urlpatterns = [
    path('preferences/me/', NotificationPreferenceViewSet.as_view({'get': 'get_preferences', 'put': 'update_preferences'}), name='my_preferences'),
    path('preferences/<str:staff_id>/', NotificationPreferenceViewSet.as_view({'get': 'get_preferences', 'put': 'update_preferences'}), name='staff_preferences'),
    path('', include(router.urls)),
]
