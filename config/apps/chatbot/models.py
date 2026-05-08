"""
Models for the AI Chatbot & RAG system.

Stores chat conversations, messages, embeddings cache, and RAG context.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Conversation(models.Model):
    """
    A chat conversation between a user and the AI assistant.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
        verbose_name=_("User"),
    )
    title = models.CharField(
        max_length=200, blank=True, verbose_name=_("Conversation Title")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_("Metadata"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Conversation")
        verbose_name_plural = _("Conversations")
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["user", "-updated_at"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.title or 'Untitled'}"


class Message(models.Model):
    """
    A single message within a conversation.
    """

    class Role(models.TextChoices):
        USER = "user", _("User")
        ASSISTANT = "assistant", _("Assistant")
        SYSTEM = "system", _("System")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name=_("Conversation"),
    )
    role = models.CharField(
        max_length=10, choices=Role.choices, verbose_name=_("Role")
    )
    content = models.TextField(verbose_name=_("Content"))
    metadata = models.JSONField(
        default=dict, blank=True, verbose_name=_("Metadata"),
        help_text=_("Stores token count, model info, sources, etc."),
    )
    tokens_used = models.PositiveIntegerField(
        default=0, verbose_name=_("Tokens Used")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Message")
        verbose_name_plural = _("Messages")
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self) -> str:
        return f"{self.role}: {self.content[:50]}..."


class DocumentEmbedding(models.Model):
    """
    Stores vector embeddings for RAG (Retrieval-Augmented Generation).

    Each document chunk is embedded and stored here for semantic search.
    """

    class DocumentType(models.TextChoices):
        EMPLOYEE = "EMPLOYEE", _("Employee Data")
        POLICY = "POLICY", _("HR Policy")
        LEAVE = "LEAVE", _("Leave Policy")
        PAYROLL = "PAYROLL", _("Payroll Info")
        ATTENDANCE = "ATTENDANCE", _("Attendance Policy")
        GENERAL = "GENERAL", _("General HR Info")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_type = models.CharField(
        max_length=20, choices=DocumentType.choices, default=DocumentType.GENERAL
    )
    content = models.TextField(verbose_name=_("Content"))
    embedding = models.JSONField(
        null=True, blank=True, verbose_name=_("Embedding Vector"),
        help_text=_("Vector embedding as JSON array (1536 dimensions)"),
    )
    metadata = models.JSONField(
        default=dict, blank=True, verbose_name=_("Metadata"),
        help_text=_("Source document metadata (ID, type, date, etc.)"),
    )
    chunk_index = models.PositiveIntegerField(
        default=0, verbose_name=_("Chunk Index")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Document Embedding")
        verbose_name_plural = _("Document Embeddings")
        ordering = ["document_type", "chunk_index"]
        indexes = [
            models.Index(fields=["document_type"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.document_type} - Chunk {self.chunk_index}"


class ChatFeedback(models.Model):
    """
    User feedback on AI assistant responses.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="feedback",
        verbose_name=_("Message"),
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(1, "Thumbs Down"), (2, "Neutral"), (3, "Thumbs Up")],
        verbose_name=_("Rating"),
    )
    feedback_text = models.TextField(blank=True, verbose_name=_("Feedback Text"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Chat Feedback")
        verbose_name_plural = _("Chat Feedback")
        unique_together = ["message"]

    def __str__(self) -> str:
        return f"Feedback for {self.message} - Rating: {self.rating}"
