"""
Admin configuration for the Chatbot app.
"""

from django.contrib import admin

from .models import ChatFeedback, Conversation, DocumentEmbedding, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "is_active", "created_at", "updated_at"]
    list_filter = ["is_active"]
    search_fields = ["user__username", "title"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["conversation", "role", "content_preview", "tokens_used", "created_at"]
    list_filter = ["role"]
    search_fields = ["content"]

    def content_preview(self, obj: Message) -> str:
        return obj.content[:75] + ("..." if len(obj.content) > 75 else "")
    content_preview.short_description = "Content"


@admin.register(DocumentEmbedding)
class DocumentEmbeddingAdmin(admin.ModelAdmin):
    list_display = ["document_type", "chunk_index", "is_active", "created_at"]
    list_filter = ["document_type", "is_active"]


@admin.register(ChatFeedback)
class ChatFeedbackAdmin(admin.ModelAdmin):
    list_display = ["message", "rating", "created_at"]
    list_filter = ["rating"]
