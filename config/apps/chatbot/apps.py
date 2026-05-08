from django.apps import AppConfig


class ChatbotConfig(AppConfig):
    """Configuration for the Chatbot app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "config.apps.chatbot"
    label = "chatbot"
    verbose_name = "AI Chatbot & RAG"
