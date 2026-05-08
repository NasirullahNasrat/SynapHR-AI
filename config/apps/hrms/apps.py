from django.apps import AppConfig


class HrmsConfig(AppConfig):
    """Configuration for the HRMS core app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "config.apps.hrms"
    label = "hrms"
    verbose_name = "HRMS Core"

    def ready(self) -> None:
        """Import signals when the app is ready."""
        import config.apps.hrms.signals  # noqa: F401
