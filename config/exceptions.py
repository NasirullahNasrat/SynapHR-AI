"""
Custom exception handler for consistent error responses across the API.
"""

import logging
import traceback

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import APIException, Throttled
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc: Exception, context: dict) -> Response | None:
    """
    Custom exception handler that returns consistent JSON error responses.

    Args:
        exc: The exception instance
        context: Dictionary containing the request, view, args, kwargs

    Returns:
        Response object with standardized error format, or None for unhandled exceptions
    """
    # Get the default response from DRF's exception handler
    response = exception_handler(exc, context)

    if response is not None:
        # Standardize the error response format
        errors = _format_errors(response, exc)
        response.data = {
            "success": False,
            "status_code": response.status_code,
            "message": _get_error_message(response.status_code, exc),
            "errors": errors,
        }
        return response

    # Handle non-DRF exceptions
    if isinstance(exc, Http404):
        return Response(
            {
                "success": False,
                "status_code": status.HTTP_404_NOT_FOUND,
                "message": "Resource not found.",
                "errors": None,
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, PermissionDenied):
        return Response(
            {
                "success": False,
                "status_code": status.HTTP_403_FORBIDDEN,
                "message": "You do not have permission to perform this action.",
                "errors": None,
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    if isinstance(exc, ValidationError):
        return Response(
            {
                "success": False,
                "status_code": status.HTTP_400_BAD_REQUEST,
                "message": "Validation error.",
                "errors": exc.message_dict if hasattr(exc, "message_dict") else str(exc),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Log unhandled exceptions
    logger.error(
        "Unhandled exception: %s\n%s",
        str(exc),
        traceback.format_exc(),
    )

    # Return a generic 500 error for unhandled exceptions
    return Response(
        {
            "success": False,
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "message": "An unexpected error occurred. Please try again later.",
            "errors": None,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def _format_errors(response: Response, exc: Exception) -> dict | list | str | None:
    """
    Format error messages into a consistent structure.

    Args:
        response: The DRF response object
        exc: The original exception

    Returns:
        Formatted error messages
    """
    if isinstance(response.data, dict):
        formatted = {}
        for field, messages in response.data.items():
            if isinstance(messages, list):
                formatted[field] = [str(msg) for msg in messages]
            else:
                formatted[field] = str(messages)
        return formatted

    if isinstance(response.data, list):
        return [str(item) for item in response.data]

    return str(response.data) if response.data else None


def _get_error_message(status_code: int, exc: Exception) -> str:
    """
    Get a human-readable error message based on status code.

    Args:
        status_code: HTTP status code
        exc: The original exception

    Returns:
        Human-readable error message
    """
    messages = {
        status.HTTP_400_BAD_REQUEST: "The request was invalid.",
        status.HTTP_401_UNAUTHORIZED: "Authentication credentials were not provided or are invalid.",
        status.HTTP_403_FORBIDDEN: "You do not have permission to perform this action.",
        status.HTTP_404_NOT_FOUND: "The requested resource was not found.",
        status.HTTP_405_METHOD_NOT_ALLOWED: "This HTTP method is not allowed for this endpoint.",
        status.HTTP_409_CONFLICT: "The request conflicts with the current state of the resource.",
        status.HTTP_429_TOO_MANY_REQUESTS: "Too many requests. Please try again later.",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "An internal server error occurred.",
    }

    if isinstance(exc, Throttled):
        wait_time = getattr(exc, "wait", None)
        if wait_time:
            return f"Too many requests. Please try again in {int(wait_time)} seconds."

    return messages.get(status_code, str(exc))


class ServiceUnavailable(APIException):
    """Exception for when a dependent service is unavailable."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Service temporarily unavailable, please try again later."
    default_code = "service_unavailable"


class ConflictError(APIException):
    """Exception for resource conflicts."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "Resource conflict detected."
    default_code = "conflict"


class BadRequest(APIException):
    """Exception for bad requests."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Bad request."
    default_code = "bad_request"
