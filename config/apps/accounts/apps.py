from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuration for the accounts app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "config.apps.accounts"
    label = "accounts"
    verbose_name = "Accounts & Authentication"
