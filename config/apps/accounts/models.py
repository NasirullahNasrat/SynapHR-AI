"""
Custom User model for SynapHR AI.

Extends Django's AbstractUser to add HRMS-specific fields and functionality.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom user model with additional fields for HRMS.

    Extends Django's AbstractUser to include employee-specific fields
    like employee ID, phone number, department, and profile image.
    """

    class Gender(models.TextChoices):
        MALE = "M", _("Male")
        FEMALE = "F", _("Female")
        OTHER = "O", _("Other")
        PREFER_NOT_TO_SAY = "N", _("Prefer not to say")

    class UserType(models.TextChoices):
        ADMIN = "ADMIN", _("Administrator")
        HR = "HR", _("HR Manager")
        MANAGER = "MANAGER", _("Manager")
        EMPLOYEE = "EMPLOYEE", _("Employee")

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name=_("Employee ID"),
        help_text=_("Unique employee identifier (e.g., EMP-0001)"),
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        verbose_name=_("Phone Number"),
    )
    gender = models.CharField(
        max_length=1,
        choices=Gender.choices,
        default=Gender.PREFER_NOT_TO_SAY,
        verbose_name=_("Gender"),
    )
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.EMPLOYEE,
        verbose_name=_("User Type"),
        help_text=_("Determines the user's role and permissions in the system"),
    )
    profile_image = models.ImageField(
        upload_to="profiles/",
        blank=True,
        null=True,
        verbose_name=_("Profile Image"),
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("Date of Birth"),
    )
    is_online = models.BooleanField(
        default=False,
        verbose_name=_("Is Online"),
        help_text=_("Indicates if the user is currently online"),
    )
    last_activity = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Last Activity"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At"),
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At"),
    )

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["employee_id"]),
            models.Index(fields=["user_type"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        """Return string representation of the user."""
        if self.employee_id:
            return f"{self.get_full_name() or self.username} ({self.employee_id})"
        return self.get_full_name() or self.username

    def save(self, *args: Any, **kwargs: Any) -> None:
        """
        Override save to auto-generate employee_id if not set.

        The employee ID format is EMP-XXXX where XXXX is a zero-padded number.
        """
        if not self.employee_id:
            last_user = User.objects.filter(employee_id__startswith="EMP-").order_by(
                "employee_id"
            ).last()
            if last_user and last_user.employee_id:
                last_num = int(last_user.employee_id.split("-")[1])
                new_num = last_num + 1
            else:
                new_num = 1
            self.employee_id = f"EMP-{new_num:04d}"
        super().save(*args, **kwargs)

    def get_initials(self) -> str:
        """Get user's initials from first and last name."""
        first = self.first_name[0] if self.first_name else ""
        last = self.last_name[0] if self.last_name else ""
        return (first + last).upper() or self.username[0:2].upper()
