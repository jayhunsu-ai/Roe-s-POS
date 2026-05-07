import json
from urllib.parse import parse_qs

from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = await self._get_user_from_token()
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return
        if self.user.role != 'Administrator':
            await self.close(code=4003)
            return

        self.global_group = 'notifications_admin_all'
        self.user_group = f'notifications_admin_{self.user.staffId}'

        await self.channel_layer.group_add(self.global_group, self.channel_name)
        await self.channel_layer.group_add(self.user_group, self.channel_name)
        await self.accept()
        await self.send(
            text_data=json.dumps(
                {'type': 'connected', 'message': 'Notification websocket connected'}
            )
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'global_group'):
            await self.channel_layer.group_discard(self.global_group, self.channel_name)
        if hasattr(self, 'user_group'):
            await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        # Read-only channel; we intentionally ignore incoming payloads.
        return

    async def notification_event(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    'type': 'notification',
                    'notification': event.get('notification', {}),
                }
            )
        )

    async def _get_user_from_token(self):
        try:
            query_string = self.scope.get('query_string', b'').decode('utf-8')
            token_value = parse_qs(query_string).get('token', [None])[0]
            if not token_value:
                return None

            token = AccessToken(token_value)
            user_id = token.get('staffId')
            if not user_id:
                return None

            User = get_user_model()
            return await User.objects.aget(staffId=user_id, is_active=True)
        except Exception:
            return None
