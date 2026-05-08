"""
Celery tasks for the accounts app.

Handles background operations like token cleanup and email notifications.
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="clean_expired_tokens")
def clean_expired_tokens() -> dict:
    """
    Clean up expired JWT tokens from the blacklist.

    This task runs daily to remove expired tokens from the database,
    preventing the token blacklist table from growing indefinitely.

    Returns:
        dict: Summary of the cleanup operation
    """
    try:
        from rest_framework_simplejwt.token_blacklist.models import (
            BlacklistedToken,
            OutstandingToken,
        )

        # Delete expired outstanding tokens
        expired_outstanding = OutstandingToken.objects.filter(
            expires_at__lt=timezone.now()
        )
        outstanding_count = expired_outstanding.count()
        expired_outstanding.delete()

        # Delete blacklisted tokens older than 7 days
        cutoff = timezone.now() - timezone.timedelta(days=7)
        old_blacklisted = BlacklistedToken.objects.filter(
            blacklisted_at__lt=cutoff
        )
        blacklisted_count = old_blacklisted.count()
        old_blacklisted.delete()

        logger.info(
            "Cleaned up %d expired outstanding tokens and %d old blacklisted tokens",
            outstanding_count,
            blacklisted_count,
        )

        return {
            "status": "success",
            "expired_outstanding_removed": outstanding_count,
            "old_blacklisted_removed": blacklisted_count,
        }

    except Exception as e:
        logger.error("Failed to clean expired tokens: %s", str(e))
        return {
            "status": "error",
            "error": str(e),
        }
