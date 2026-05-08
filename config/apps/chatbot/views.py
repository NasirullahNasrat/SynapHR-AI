"""
Views for the Chatbot app.

Provides REST API endpoints for AI chat, RAG document management,
conversation history, and feedback collection.
"""

from __future__ import annotations

import json
import logging

from rest_framework import generics, permissions, status, views
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from config.pagination import StandardPagination

from .models import ChatFeedback, Conversation, DocumentEmbedding, Message
from .serializers import (
    ChatFeedbackSerializer,
    ChatRequestSerializer,
    ConversationSerializer,
    DocumentEmbeddingSerializer,
    DocumentIngestSerializer,
    MessageSerializer,
)
from .services import (
    DeepSeekClient,
    LocalIntentParser,
    RAGEngine,
    HRMS_FUNCTIONS,
    get_deepseek_client,
    get_hrms_tools,
    get_rag_engine,
)

logger = logging.getLogger(__name__)


class IsAdminOrHRForChatbot(permissions.BasePermission):
    """
    Permission for AI Chatbot features.

    ADMIN, HR, and MANAGER can use the AI chatbot.
    Regular EMPLOYEE role is restricted from AI features.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type in (
            "ADMIN", "HR", "MANAGER",
        )


# =============================================================================
# Conversation Views
# =============================================================================


class ConversationListCreateView(generics.ListCreateAPIView):
    """GET/POST api/v1/chatbot/conversations/"""

    serializer_class = ConversationSerializer
    permission_classes = [IsAdminOrHRForChatbot]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user).prefetch_related(
            "messages"
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ConversationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE api/v1/chatbot/conversations/{id}/"""

    serializer_class = ConversationSerializer
    permission_classes = [IsAdminOrHRForChatbot]

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)


# =============================================================================
# Message Views
# =============================================================================


class MessageListView(generics.ListAPIView):
    """GET api/v1/chatbot/conversations/{id}/messages/"""

    serializer_class = MessageSerializer
    permission_classes = [IsAdminOrHRForChatbot]
    pagination_class = StandardPagination

    def get_queryset(self):
        return Message.objects.filter(
            conversation_id=self.kwargs["conversation_id"],
            conversation__user=self.request.user,
        ).order_by("created_at")


# =============================================================================
# Chat View (Main AI Interaction)
# =============================================================================


@api_view(["POST"])
@permission_classes([IsAdminOrHRForChatbot])
def chat(request):
    """
    POST api/v1/chatbot/chat/

    Send a message to the AI assistant and get a response.

    Uses RAG (Retrieval-Augmented Generation) to provide context-aware
    responses based on company HR documents and policies, AND function/tool
    calling to interact with live HRMS data (employees, departments,
    attendance, leaves, payroll, performance, etc.).
    """
    serializer = ChatRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user_message_text = serializer.validated_data["message"]
    conversation_id = serializer.validated_data.get("conversation_id")
    document_type = serializer.validated_data.get("document_type", "")

    # Get or create conversation
    if conversation_id:
        try:
            conversation = Conversation.objects.get(
                id=conversation_id, user=request.user
            )
        except Conversation.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "Conversation not found.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
    else:
        # Create new conversation with title from first message
        title = user_message_text[:100] + ("..." if len(user_message_text) > 100 else "")
        conversation = Conversation.objects.create(
            user=request.user,
            title=title,
        )

    # Save user message
    user_message = Message.objects.create(
        conversation=conversation,
        role="user",
        content=user_message_text,
    )

    # Get AI client, RAG engine, and HRMS tools
    ai_client = get_deepseek_client()
    rag_engine = get_rag_engine()
    hrms_tools = get_hrms_tools(request.user)

    # Check if DeepSeek AI is available
    ai_available = ai_client.is_available()

    if ai_available:
        # ---- DeepSeek AI Path ----
        # Build context from RAG
        context = rag_engine.build_context(
            user_message_text,
            document_type=document_type if document_type else None,
        )

        # Prepare messages for the AI
        system_prompt = rag_engine.get_system_prompt()
        if context:
            system_prompt += f"\n\nRelevant context from company documents:\n{context}"

        # Get conversation history (last 10 messages for context)
        history_messages = Message.objects.filter(conversation=conversation).order_by(
            "-created_at"
        )[:10]

        ai_messages = [{"role": "system", "content": system_prompt}]

        # Add history in reverse chronological order
        for msg in reversed(history_messages):
            ai_messages.append({"role": msg.role, "content": msg.content})

        # Add the new user message
        ai_messages.append({"role": "user", "content": user_message_text})

        # Maximum number of function call iterations to prevent infinite loops
        max_iterations = 5
        iteration = 0
        final_content = None
        tokens_used_total = 0
        tool_results: list[dict[str, Any]] = []

        while iteration < max_iterations:
            iteration += 1

            # Get AI response with function definitions
            ai_response = ai_client.chat_completion(
                ai_messages,
                functions=HRMS_FUNCTIONS,
            )

            if not ai_response:
                break

            tokens_used_total += ai_response.get("tokens_used", 0)

            # Check if the AI wants to call a function
            function_call = ai_response.get("function_call")

            if function_call:
                function_name = function_call["name"]
                try:
                    function_args = json.loads(function_call["arguments"])
                except (json.JSONDecodeError, TypeError):
                    function_args = {}

                logger.info(
                    "AI calling function: %s with args: %s",
                    function_name,
                    function_args,
                )

                # Execute the function
                try:
                    function_result = hrms_tools.execute(function_name, **function_args)
                except Exception as e:
                    function_result = json.dumps({
                        "error": f"Error executing {function_name}: {str(e)}"
                    })
                    logger.error("Function execution error: %s", str(e), exc_info=True)

                # Add the assistant's function call message
                ai_messages.append({
                    "role": "assistant",
                    "content": ai_response.get("content", ""),
                    "tool_calls": [{
                        "id": f"call_{function_name}",
                        "type": "function",
                        "function": {
                            "name": function_name,
                            "arguments": function_call["arguments"],
                        },
                    }],
                })

                # Add the function result as a tool response
                ai_messages.append({
                    "role": "tool",
                    "tool_call_id": f"call_{function_name}",
                    "content": function_result,
                })

                # Keep track of tool results for response payload/metadata
                try:
                    parsed_result = json.loads(function_result)
                except Exception:
                    parsed_result = function_result
                tool_results.append({
                    "name": function_name,
                    "arguments": function_args,
                    "result": parsed_result,
                })
            else:
                # No function call - this is the final response
                final_content = ai_response.get("content", "")
                break

        if final_content:
            # Save assistant message
            assistant_message = Message.objects.create(
                conversation=conversation,
                role="assistant",
                content=final_content,
                tokens_used=tokens_used_total,
                metadata={
                    "model": ai_response.get("model", "deepseek-chat") if ai_response else "unknown",
                    "context_used": bool(context),
                    "function_calls": iteration - 1 if iteration > 1 else 0,
                    "tool_results": tool_results,
                    "last_tool_result": tool_results[-1] if tool_results else None,
                },
            )

            # Get sources for the response
            sources = rag_engine.search_similar(
                user_message_text,
                document_type=document_type if document_type else None,
                top_k=3,
            )

            return Response(
                {
                    "success": True,
                        "data": {
                            "conversation_id": conversation.id,
                            "user_message": MessageSerializer(user_message).data,
                            "assistant_message": MessageSerializer(assistant_message).data,
                            "sources": sources,
                            "tool_results": tool_results,
                            "last_tool_result": tool_results[-1] if tool_results else None,
                        },
                    }
                )

    # ---- Local Fallback Path (when DeepSeek is unavailable) ----
    logger.info(
        "DeepSeek AI unavailable. Using LocalIntentParser fallback for: %s",
        user_message_text[:100],
    )

    local_parser = LocalIntentParser(hrms_tools)
    fallback_content = local_parser.process_message(user_message_text)

    assistant_message = Message.objects.create(
        conversation=conversation,
        role="assistant",
        content=fallback_content,
        metadata={
            "fallback": True,
            "mode": "local_intent_parser",
        },
    )

    return Response(
        {
            "success": True,
            "data": {
                "conversation_id": conversation.id,
                "user_message": MessageSerializer(user_message).data,
                "assistant_message": MessageSerializer(assistant_message).data,
                "sources": [],
                "note": "AI service unavailable. Using local intent parser fallback.",
            },
        }
    )


# =============================================================================
# Document Embedding Views
# =============================================================================


class DocumentEmbeddingListCreateView(generics.ListCreateAPIView):
    """GET/POST api/v1/chatbot/documents/"""

    serializer_class = DocumentEmbeddingSerializer
    permission_classes = [IsAdminOrHRForChatbot]
    pagination_class = StandardPagination
    filterset_fields = ["document_type", "is_active"]

    def get_queryset(self):
        return DocumentEmbedding.objects.all()


class DocumentEmbeddingDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE api/v1/chatbot/documents/{id}/"""

    queryset = DocumentEmbedding.objects.all()
    serializer_class = DocumentEmbeddingSerializer
    permission_classes = [IsAdminOrHRForChatbot]


@api_view(["POST"])
@permission_classes([IsAdminOrHRForChatbot])
def ingest_document(request):
    """
    POST api/v1/chatbot/documents/ingest/

    Ingest a document into the RAG system. The document is chunked,
    embedded, and stored for semantic search.
    """
    serializer = DocumentIngestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    document_type = serializer.validated_data["document_type"]
    content = serializer.validated_data["content"]
    metadata = serializer.validated_data.get("metadata", {})

    ai_client = get_deepseek_client()
    rag_engine = get_rag_engine()

    # Chunk the document
    chunks = rag_engine.chunk_text(content)

    created_count = 0
    for i, chunk in enumerate(chunks):
        # Generate embedding
        embedding = ai_client.generate_embedding(chunk)

        # Store in database
        DocumentEmbedding.objects.create(
            document_type=document_type,
            content=chunk,
            embedding=embedding,
            metadata=metadata,
            chunk_index=i,
        )
        created_count += 1

    return Response(
        {
            "success": True,
            "message": f"Document ingested successfully. Created {created_count} chunks.",
            "data": {
                "document_type": document_type,
                "chunks_created": created_count,
                "total_characters": len(content),
            },
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAdminOrHRForChatbot])
def search_documents(request):
    """
    POST api/v1/chatbot/documents/search/

    Search for documents using semantic search.
    """
    query = request.data.get("query", "")
    document_type = request.data.get("document_type")
    top_k = request.data.get("top_k", 5)

    if not query:
        return Response(
            {"success": False, "message": "Query is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    rag_engine = get_rag_engine()
    results = rag_engine.search_similar(
        query,
        document_type=document_type if document_type else None,
        top_k=min(top_k, 20),
    )

    return Response(
        {
            "success": True,
            "data": {
                "query": query,
                "results_count": len(results),
                "results": results,
            },
        }
    )


# =============================================================================
# Feedback Views
# =============================================================================


@api_view(["POST"])
@permission_classes([IsAdminOrHRForChatbot])
def submit_feedback(request):
    """
    POST api/v1/chatbot/feedback/

    Submit feedback for an AI assistant response.
    """
    serializer = ChatFeedbackSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # Verify the message belongs to the user's conversation
    try:
        message = Message.objects.get(
            id=serializer.validated_data["message"].id,
            conversation__user=request.user,
        )
    except Message.DoesNotExist:
        return Response(
            {"success": False, "message": "Message not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Check if feedback already exists
    if ChatFeedback.objects.filter(message=message).exists():
        return Response(
            {"success": False, "message": "Feedback already submitted for this message."},
            status=status.HTTP_409_CONFLICT,
        )

    feedback = ChatFeedback.objects.create(
        message=message,
        rating=serializer.validated_data["rating"],
        feedback_text=serializer.validated_data.get("feedback_text", ""),
    )

    return Response(
        {
            "success": True,
            "message": "Feedback submitted successfully.",
            "data": ChatFeedbackSerializer(feedback).data,
        },
        status=status.HTTP_201_CREATED,
    )


# =============================================================================
# Health Check
# =============================================================================


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def ai_health_check(request):
    """
    GET api/v1/chatbot/health/

    Check if the AI service is configured and available.
    Returns the active provider, model, and configuration status
    so the frontend can dynamically display provider info.

    NOTE: This is a lightweight check that only verifies configuration.
    For a full connection test (actual API call), use POST /chatbot/test-connection/.
    """
    ai_client = get_deepseek_client()

    is_avail = ai_client.is_available()

    return Response(
        {
            "success": True,
            "data": {
                "ai_service_available": is_avail,
                "local_fallback_available": True,
                "active_provider": ai_client.provider if is_avail else None,
                "model": ai_client.model if is_avail else None,
                "base_url": ai_client.base_url if is_avail else None,
                "embedding_model": ai_client.embedding_model if is_avail else None,
            },
        }
    )


@api_view(["POST"])
@permission_classes([IsAdminOrHRForChatbot])
def test_ai_connection(request):
    """
    POST api/v1/chatbot/test-connection/

    Actually test the AI API connection by making a minimal API call.
    This is used by the Settings page "Test Connection" button to verify
    that the configured API key, base URL, and model are working correctly.

    Returns:
        success: True if the API call succeeded
        message: Human-readable result message
        provider: The active provider name
        model: The model used for the test
    """
    ai_client = get_deepseek_client()

    if not ai_client.is_available():
        return Response(
            {
                "success": False,
                "message": "AI client is not configured. Please add an API key in Settings.",
                "provider": ai_client.provider,
                "model": ai_client.model,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    result = ai_client.test_connection()

    if result["success"]:
        return Response(
            {
                "success": True,
                "message": result["message"],
                "provider": ai_client.provider,
                "model": result.get("model", ai_client.model),
            }
        )
    else:
        return Response(
            {
                "success": False,
                "message": result["message"],
                "provider": ai_client.provider,
                "model": ai_client.model,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
