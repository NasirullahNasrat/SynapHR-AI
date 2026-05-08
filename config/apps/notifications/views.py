"""
Views for the Notifications app.

Provides REST API endpoints for managing WebSocket connections
and notification preferences.
"""

from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def websocket_token(request):
    """
    GET api/v1/notifications/ws-token/

    Get a WebSocket authentication token for establishing
    a real-time notification connection.
    """
    from rest_framework_simplejwt.tokens import AccessToken

    token = AccessToken.for_user(request.user)

    return Response(
        {
            "success": True,
            "data": {
                "ws_url": f"ws://{request.get_host()}/ws/notifications/",
                "token": str(token),
            },
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def notification_preferences(request):
    """
    GET/PUT api/v1/notifications/preferences/

    Get or update notification preferences for the authenticated user.
    """
    # For now, return default preferences
    # In production, this would be stored in a UserPreferences model
    return Response(
        {
            "success": True,
            "data": {
                "email_notifications": True,
                "push_notifications": True,
                "leave_requests": True,
                "payroll_updates": True,
                "attendance_reminders": True,
                "performance_reviews": True,
            },
        }
    )
