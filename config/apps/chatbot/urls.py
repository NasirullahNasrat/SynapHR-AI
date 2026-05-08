"""
URL configuration for the Chatbot app.
"""

from django.urls import path

from . import views

app_name = "chatbot"

urlpatterns = [
    # Health Check
    path("health/", views.ai_health_check, name="ai-health"),
    # Connection Test (actual API call to verify credentials)
    path("test-connection/", views.test_ai_connection, name="test-connection"),
    # Conversations
    path("conversations/", views.ConversationListCreateView.as_view(), name="conversation-list"),
    path("conversations/<uuid:pk>/", views.ConversationDetailView.as_view(), name="conversation-detail"),
    path("conversations/<uuid:conversation_id>/messages/", views.MessageListView.as_view(), name="message-list"),
    # Chat
    path("chat/", views.chat, name="chat"),
    # Document Management
    path("documents/", views.DocumentEmbeddingListCreateView.as_view(), name="document-list"),
    path("documents/<uuid:pk>/", views.DocumentEmbeddingDetailView.as_view(), name="document-detail"),
    path("documents/ingest/", views.ingest_document, name="document-ingest"),
    path("documents/search/", views.search_documents, name="document-search"),
    # Feedback
    path("feedback/", views.submit_feedback, name="feedback"),
]
