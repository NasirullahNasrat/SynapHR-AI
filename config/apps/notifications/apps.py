from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """Configuration for the Notifications app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "config.apps.notifications"
    label = "notifications"
    verbose_name = "Real-time Notifications"
