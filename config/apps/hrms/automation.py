"""
Automation Rule Engine for SynapHR AI.

Provides a configurable rule-based engine that evaluates automation rules
when HRMS events occur (e.g., employee created, leave approved, attendance
marked). Rules are stored in the AutomationRule model and evaluated by
the RuleEngine class.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from django.db.models import Model

from config.apps.hrms.models import AutomationRule, Notification

logger = logging.getLogger(__name__)


class RuleEngine:
    """
    Central rule engine that evaluates AutomationRule records against events.

    Usage:
        RuleEngine.evaluate("LEAVE_APPROVED", {
            "instance": leave_request_instance,
            "request": request_object,  # optional
        })
    """

    @classmethod
    def evaluate(cls, trigger_event: str, context: dict[str, Any]) -> None:
        """
        Evaluate all active rules matching the trigger_event against the context.

        Args:
            trigger_event: The event type (e.g., "LEAVE_APPROVED")
            context: Dict containing at minimum {"instance": model_instance}
        """
        rules = AutomationRule.objects.filter(
            trigger_event=trigger_event,
            is_active=True,
        ).order_by("-priority", "name")

        if not rules.exists():
            return

        for rule in rules:
            try:
                if cls._matches_condition(rule.condition_expression, context):
                    cls._execute_action(rule.action_type, rule.action_config, context)
            except Exception as exc:
                logger.error(
                    "AutomationRule '%s' (id=%s) failed: %s",
                    rule.name,
                    rule.id,
                    exc,
                )

    @classmethod
    def _matches_condition(
        cls, condition: dict[str, Any], context: dict[str, Any]
    ) -> bool:
        """
        Check if the context matches the condition expression.

        Simple key-value matching: all keys in condition must match
        corresponding attributes on the instance or keys in context.
        """
        if not condition:
            return True

        instance = context.get("instance")
        for key, expected_value in condition.items():
            # Check context first
            if key in context:
                actual = context[key]
            elif instance and hasattr(instance, key):
                actual = getattr(instance, key)
            else:
                return False

            # Handle callable expected values (e.g., status choices)
            if callable(expected_value):
                if not expected_value(actual):
                    return False
            elif str(actual) != str(expected_value):
                return False

        return True

    @classmethod
    def _execute_action(
        cls, action_type: str, config: dict[str, Any], context: dict[str, Any]
    ) -> None:
        """Execute the configured action."""
        instance = context.get("instance")
        request = context.get("request")

        if action_type == AutomationRule.ActionType.SEND_NOTIFICATION:
            cls._action_send_notification(config, instance, request)
        elif action_type == AutomationRule.ActionType.UPDATE_FIELD:
            cls._action_update_field(config, instance)
        elif action_type == AutomationRule.ActionType.CREATE_RECORD:
            cls._action_create_record(config, instance, context)
        elif action_type == AutomationRule.ActionType.TRIGGER_WEBHOOK:
            cls._action_trigger_webhook(config, instance)
        else:
            logger.warning("Unknown action_type: %s", action_type)

    @classmethod
    def _action_send_notification(
        cls, config: dict[str, Any], instance: Model | None, request: Any
    ) -> None:
        """Send a notification based on the action config."""
        recipient = None
        recipient_field = config.get("recipient_field", "")
        if recipient_field and instance and hasattr(instance, recipient_field):
            related = getattr(instance, recipient_field)
            if related and hasattr(related, "user"):
                recipient = related.user
            elif related and hasattr(related, "id"):
                recipient = related

        if not recipient and request and hasattr(request, "user"):
            recipient = request.user

        if not recipient:
            logger.warning("No recipient resolved for notification action")
            return

        title = config.get("title", "Automated Notification")
        message = config.get("message", "")
        # Simple template substitution
        if instance:
            message = message.format(instance=instance)

        Notification.objects.create(
            recipient=recipient,
            notification_type=config.get(
                "notification_type", Notification.NotificationType.SYSTEM
            ),
            title=title,
            message=message,
            link=config.get("link", ""),
            metadata={
                "automation_rule": True,
                "source_model": instance.__class__.__name__ if instance else "",
                "source_id": str(instance.pk) if instance else "",
            },
        )

    @classmethod
    def _action_update_field(
        cls, config: dict[str, Any], instance: Model | None
    ) -> None:
        """Update a field on the instance."""
        if not instance:
            return
        field_name = config.get("field_name", "")
        field_value = config.get("field_value", "")
        if field_name and hasattr(instance, field_name):
            setattr(instance, field_name, field_value)
            instance.save(update_fields=[field_name])

    @classmethod
    def _action_create_record(
        cls, config: dict[str, Any], instance: Model | None, context: dict[str, Any]
    ) -> None:
        """Create a new record (placeholder for future expansion)."""
        logger.info(
            "CREATE_RECORD action triggered: config=%s, instance=%s",
            config,
            instance,
        )

    @classmethod
    def _action_trigger_webhook(
        cls, config: dict[str, Any], instance: Model | None
    ) -> None:
        """Trigger a webhook URL with instance data."""
        url = config.get("url", "")
        if not url:
            logger.warning("No URL configured for webhook action")
            return
        # Fire-and-forget: log the intent (actual HTTP call would go here)
        logger.info(
            "Webhook triggered: url=%s, instance_id=%s",
            url,
            str(instance.pk) if instance else "N/A",
        )
