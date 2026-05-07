from django.urls import re_path

from notifications.consumers import NotificationConsumer


websocket_urlpatterns = [
    re_path(r'^ws/notifications/$', NotificationConsumer.as_asgi()),
    re_path(r'^api/v1/ws/notifications/$', NotificationConsumer.as_asgi()),
]
