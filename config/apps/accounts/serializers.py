"""
Serializers for the accounts app.

Handles user registration, login, profile management, and password reset.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model, password_validation
from django.core import exceptions as django_exceptions
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.

    Provides a read/write representation of user data with proper
    field validation and password handling.
    """

    password = serializers.CharField(
        write_only=True,
        required=False,
        style={"input_type": "password"},
        help_text="Password for the user account",
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=False,
        style={"input_type": "password"},
        help_text="Confirm password (must match password)",
    )
    full_name = serializers.SerializerMethodField(read_only=True)
    initials = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
            "confirm_password",
            "first_name",
            "last_name",
            "full_name",
            "initials",
            "employee_id",
            "phone_number",
            "gender",
            "user_type",
            "profile_image",
            "date_of_birth",
            "is_active",
            "is_online",
            "last_activity",
            "date_joined",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "employee_id",
            "is_online",
            "last_activity",
            "date_joined",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "username": {
                "help_text": "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
            },
            "email": {"required": True},
        }

    def get_full_name(self, obj: User) -> str:
        """Get the full name of the user."""
        return obj.get_full_name()

    def get_initials(self, obj: User) -> str:
        """Get the initials of the user."""
        return obj.get_initials()

    def validate(self, attrs: dict) -> dict:
        """Validate password confirmation and password strength."""
        if "password" in attrs:
            password = attrs.get("password")
            confirm_password = attrs.pop("confirm_password", None)

            if password and password != confirm_password:
                raise serializers.ValidationError(
                    {"confirm_password": "Passwords do not match."}
                )

            # Validate password strength
            try:
                password_validation.validate_password(password)
            except django_exceptions.ValidationError as e:
                raise serializers.ValidationError({"password": list(e.messages)})

        return attrs

    def create(self, validated_data: dict) -> User:
        """Create a new user with encrypted password."""
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance: User, validated_data: dict) -> User:
        """Update user instance, handling password changes."""
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class UserListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing users.

    Excludes sensitive fields like email and includes only essential info.
    """

    full_name = serializers.SerializerMethodField()
    initials = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "initials",
            "employee_id",
            "user_type",
            "profile_image",
            "is_active",
            "is_online",
        ]

    def get_full_name(self, obj: User) -> str:
        return obj.get_full_name()

    def get_initials(self, obj: User) -> str:
        return obj.get_initials()


class AdminUserSerializer(serializers.ModelSerializer):
    """
    Serializer for ADMIN/HR to update user roles and status.

    Allows updating user_type, is_active, and other management fields
    without requiring all user fields (password, email, etc.).
    """

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "employee_id",
            "phone_number",
            "gender",
            "user_type",
            "profile_image",
            "is_active",
            "is_online",
            "last_activity",
            "date_joined",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "username",
            "email",
            "employee_id",
            "is_online",
            "last_activity",
            "date_joined",
            "created_at",
            "updated_at",
            "profile_image",
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for changing user password.

    Requires the old password for verification and the new password
    with confirmation.
    """

    old_password = serializers.CharField(
        required=True,
        style={"input_type": "password"},
        help_text="Current password",
    )
    new_password = serializers.CharField(
        required=True,
        style={"input_type": "password"},
        help_text="New password",
    )
    confirm_new_password = serializers.CharField(
        required=True,
        style={"input_type": "password"},
        help_text="Confirm new password",
    )

    def validate_old_password(self, value: str) -> str:
        """Verify the old password is correct."""
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs: dict) -> dict:
        """Validate new password and confirmation match."""
        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise serializers.ValidationError(
                {"confirm_new_password": "New passwords do not match."}
            )
        if attrs["old_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {"new_password": "New password cannot be the same as the old password."}
            )
        try:
            password_validation.validate_password(attrs["new_password"])
        except django_exceptions.ValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})
        return attrs


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user login.

    Accepts username/email and password for authentication.
    """

    username = serializers.CharField(
        required=True,
        help_text="Username or email address",
    )
    password = serializers.CharField(
        required=True,
        style={"input_type": "password"},
        help_text="Password",
    )


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for requesting a password reset email."""

    email = serializers.EmailField(required=True, help_text="Registered email address")


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for confirming a password reset with token."""

    token = serializers.CharField(required=True, help_text="Password reset token")
    password = serializers.CharField(
        required=True,
        style={"input_type": "password"},
        help_text="New password",
    )
    confirm_password = serializers.CharField(
        required=True,
        style={"input_type": "password"},
        help_text="Confirm new password",
    )

    def validate(self, attrs: dict) -> dict:
        """Validate passwords match and meet strength requirements."""
        if attrs["password"] != attrs["confirm_password"]:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )
        try:
            password_validation.validate_password(attrs["password"])
        except django_exceptions.ValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return attrs
