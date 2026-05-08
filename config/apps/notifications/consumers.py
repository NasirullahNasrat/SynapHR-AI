"""
WebSocket consumers for real-time notifications.

Uses Django Channels to provide real-time notification delivery
to connected clients.
"""

from __future__ import annotations

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model

from config.apps.hrms.models import Notification

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications.

    Each user gets a personal notification channel based on their user ID.
    The consumer handles connection, disconnection, and message delivery.
    """

    async def connect(self) -> None:
        """Handle WebSocket connection."""
        self.user = self.scope.get("user")

        if not self.user or not self.user.is_authenticated:
            logger.warning("Unauthenticated WebSocket connection attempt rejected.")
            await self.close()
            return

        # Create a unique group name for this user
        self.group_name = f"notifications_{self.user.id}"

        # Join the user's notification group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()

        # Send unread count on connection
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            "type": "connection_established",
            "message": "Connected to notification service.",
            "unread_count": unread_count,
        }))

        logger.info(
            "WebSocket connected: user=%s, group=%s",
            self.user.username,
            self.group_name,
        )

    async def disconnect(self, close_code: int) -> None:
        """Handle WebSocket disconnection."""
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )
            logger.info(
                "WebSocket disconnected: user=%s, group=%s",
                self.user.username if self.user else "unknown",
                self.group_name,
            )

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        """
        Handle incoming WebSocket messages.

        Currently supports:
        - ping: Keep-alive message
        - mark_read: Mark a notification as read
        """
        if not text_data:
            return

        try:
            data = json.loads(text_data)
            message_type = data.get("type", "")

            if message_type == "ping":
                await self.send(text_data=json.dumps({
                    "type": "pong",
                }))

            elif message_type == "mark_read":
                notification_id = data.get("notification_id")
                if notification_id:
                    await self.mark_notification_read(notification_id)
                    unread_count = await self.get_unread_count()
                    await self.send(text_data=json.dumps({
                        "type": "notification_read",
                        "notification_id": notification_id,
                        "unread_count": unread_count,
                    }))

            elif message_type == "mark_all_read":
                await self.mark_all_notifications_read()
                await self.send(text_data=json.dumps({
                    "type": "all_notifications_read",
                }))

        except json.JSONDecodeError:
            logger.warning("Invalid JSON received on WebSocket.")
        except Exception as e:
            logger.error("Error processing WebSocket message: %s", str(e))

    async def send_notification(self, event: dict) -> None:
        """
        Send a notification to the WebSocket client.

        This method is called by the channel layer when a notification
        is sent to the user's group.
        """
        await self.send(text_data=json.dumps({
            "type": "notification",
            "notification": event.get("data", {}),
        }))

    async def send_unread_count(self, event: dict) -> None:
        """Send updated unread count to the client."""
        await self.send(text_data=json.dumps({
            "type": "unread_count",
            "count": event.get("count", 0),
        }))

    @database_sync_to_async
    def get_unread_count(self) -> int:
        """Get the number of unread notifications for the user."""
        return Notification.objects.filter(
            recipient=self.user,
            is_read=False,
        ).count()

    @database_sync_to_async
    def mark_notification_read(self, notification_id: str) -> None:
        """Mark a single notification as read."""
        from django.utils import timezone

        Notification.objects.filter(
            id=notification_id,
            recipient=self.user,
        ).update(is_read=True, read_at=timezone.now())

    @database_sync_to_async
    def mark_all_notifications_read(self) -> None:
        """Mark all notifications as read for the user."""
        from django.utils import timezone

        Notification.objects.filter(
            recipient=self.user,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time AI chat streaming.

    Allows streaming AI responses token by token for a better user experience.
    """

    async def connect(self) -> None:
        """Handle WebSocket connection for chat."""
        self.user = self.scope.get("user")

        if not self.user or not self.user.is_authenticated:
            await self.close()
            return

        self.conversation_id = self.scope["url_route"]["kwargs"].get("conversation_id")
        self.group_name = f"chat_{self.user.id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()
        logger.info(
            "Chat WebSocket connected: user=%s, conversation=%s",
            self.user.username,
            self.conversation_id,
        )

    async def disconnect(self, close_code: int) -> None:
        """Handle WebSocket disconnection."""
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        """Handle incoming chat messages via WebSocket."""
        if not text_data:
            return

        try:
            data = json.loads(text_data)
            message_type = data.get("type", "")

            if message_type == "chat_message":
                message = data.get("message", "")
                await self.process_chat_message(message)

        except json.JSONDecodeError:
            logger.warning("Invalid JSON received on chat WebSocket.")
        except Exception as e:
            logger.error("Error processing chat message: %s", str(e))

    async def process_chat_message(self, message: str) -> None:
        """Process a chat message and stream the response."""
        from .services import get_deepseek_client, get_rag_engine
        from .models import Conversation, Message

        # Get or create conversation
        conversation = await database_sync_to_async(
            Conversation.objects.get_or_create
        )(id=self.conversation_id, user=self.user)

        # Save user message
        user_msg = await database_sync_to_async(Message.objects.create)(
            conversation=conversation,
            role="user",
            content=message,
        )

        # Get AI response with streaming
        ai_client = get_deepseek_client()
        rag_engine = get_rag_engine()

        context = rag_engine.build_context(message)
        system_prompt = rag_engine.get_system_prompt()
        if context:
            system_prompt += f"\n\nContext:\n{context}"

        ai_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ]

        response = ai_client.chat_completion(ai_messages, stream=True)

        if response:
            full_content = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_content += content
                    await self.send(text_data=json.dumps({
                        "type": "token",
                        "content": content,
                    }))

            # Save assistant message
            await database_sync_to_async(Message.objects.create)(
                conversation=conversation,
                role="assistant",
                content=full_content,
            )

            await self.send(text_data=json.dumps({
                "type": "done",
                "full_content": full_content,
            }))
        else:
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "AI service unavailable.",
            }))

    async def chat_token(self, event: dict) -> None:
        """Forward a chat token to the WebSocket client."""
        await self.send(text_data=json.dumps({
            "type": "token",
            "content": event.get("content", ""),
        }))
