"""
WebSocket URL routing for the Chatbot app.

Maps WebSocket URL patterns for real-time chat streaming.
"""

from django.urls import re_path

from config.apps.notifications.consumers import ChatConsumer

websocket_urlpatterns = [
    re_path(
        r"ws/chat/(?P<conversation_id>[0-9a-f-]+)/$",
        ChatConsumer.as_asgi(),
        name="ws-chat",
    ),
]
