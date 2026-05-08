"""
Admin configuration for the accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for the custom User model."""

    list_display = [
        "username",
        "email",
        "employee_id",
        "first_name",
        "last_name",
        "user_type",
        "is_active",
        "is_online",
        "date_joined",
    ]
    list_filter = [
        "user_type",
        "gender",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
    ]
    search_fields = [
        "username",
        "email",
        "first_name",
        "last_name",
        "employee_id",
        "phone_number",
    ]
    ordering = ["-date_joined"]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            _("Personal Info"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "phone_number",
                    "gender",
                    "date_of_birth",
                    "profile_image",
                )
            },
        ),
        (
            _("HRMS Info"),
            {
                "fields": (
                    "employee_id",
                    "user_type",
                )
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Important dates"),
            {
                "fields": (
                    "last_login",
                    "date_joined",
                    "last_activity",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                    "user_type",
                    "first_name",
                    "last_name",
                ),
            },
        ),
    )
