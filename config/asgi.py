"""
ASGI config for SynapHR AI project.

Supports both HTTP (Django) and WebSocket (Channels) protocols.
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

django_asgi_app = get_asgi_application()

from config.apps.notifications.routing import websocket_urlpatterns as notification_ws
from config.apps.chatbot.routing import websocket_urlpatterns as chatbot_ws

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                notification_ws + chatbot_ws
            )
        ),
    }
)
