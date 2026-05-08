"""
WebSocket URL routing for the Notifications app.

Maps WebSocket URL patterns to their respective consumers.
"""

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    # Real-time notifications
    re_path(
        r"ws/notifications/$",
        consumers.NotificationConsumer.as_asgi(),
        name="ws-notifications",
    ),
    # Real-time chat streaming
    re_path(
        r"ws/chat/(?P<conversation_id>[0-9a-f-]+)/$",
        consumers.ChatConsumer.as_asgi(),
        name="ws-chat",
    ),
]
