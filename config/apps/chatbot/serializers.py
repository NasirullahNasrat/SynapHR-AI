"""
Serializers for the Chatbot app.
"""

from __future__ import annotations

from rest_framework import serializers

from .models import ChatFeedback, Conversation, DocumentEmbedding, Message


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for Conversation model."""

    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id", "user", "title", "is_active", "message_count",
            "last_message", "metadata", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]

    def get_message_count(self, obj: Conversation) -> int:
        return obj.messages.count()

    def get_last_message(self, obj: Conversation) -> str | None:
        last_msg = obj.messages.order_by("-created_at").first()
        if last_msg:
            return last_msg.content[:100]
        return None


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model."""

    class Meta:
        model = Message
        fields = [
            "id", "conversation", "role", "content",
            "metadata", "tokens_used", "created_at",
        ]
        read_only_fields = ["id", "created_at", "tokens_used"]


class ChatRequestSerializer(serializers.Serializer):
    """Serializer for chat request input."""

    conversation_id = serializers.UUIDField(
        required=False,
        help_text="Existing conversation ID. If not provided, a new conversation is created.",
    )
    message = serializers.CharField(
        required=True,
        help_text="The user's message to the AI assistant.",
    )
    document_type = serializers.ChoiceField(
        choices=[
            "", "EMPLOYEE", "POLICY", "LEAVE", "PAYROLL", "ATTENDANCE", "GENERAL",
        ],
        required=False,
        default="",
        help_text="Optional filter for RAG document type.",
    )


class ChatResponseSerializer(serializers.Serializer):
    """Serializer for chat response output."""

    conversation_id = serializers.UUIDField()
    user_message = MessageSerializer()
    assistant_message = MessageSerializer()
    sources = serializers.ListField(
        child=serializers.DictField(), required=False
    )


class DocumentEmbeddingSerializer(serializers.ModelSerializer):
    """Serializer for DocumentEmbedding model."""

    class Meta:
        model = DocumentEmbedding
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class ChatFeedbackSerializer(serializers.ModelSerializer):
    """Serializer for ChatFeedback model."""

    class Meta:
        model = ChatFeedback
        fields = ["id", "message", "rating", "feedback_text", "created_at"]
        read_only_fields = ["id", "created_at"]


class DocumentIngestSerializer(serializers.Serializer):
    """Serializer for ingesting documents into the RAG system."""

    document_type = serializers.ChoiceField(
        choices=[
            "EMPLOYEE", "POLICY", "LEAVE", "PAYROLL", "ATTENDANCE", "GENERAL",
        ]
    )
    content = serializers.CharField(help_text="The document content to ingest")
    metadata = serializers.JSONField(
        required=False, default=dict,
        help_text="Optional metadata for the document",
    )
