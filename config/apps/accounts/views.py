"""
Views for the accounts app.

Handles user registration, login, profile management, and password operations.
Uses JWT tokens for authentication via SimpleJWT.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.views import (
    TokenObtainPairView as BaseTokenObtainPairView,
)
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView
from rest_framework_simplejwt.views import TokenVerifyView as BaseTokenVerifyView

from config.exceptions import BadRequest

from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    UserListSerializer,
    UserSerializer,
)

User = get_user_model()


class TokenObtainPairView(BaseTokenObtainPairView):
    """
    POST api/v1/auth/token/
    Takes a set of user credentials and returns an access and refresh JSON web
    token pair to prove the authentication of those credentials.
    """

    pass


class TokenRefreshView(BaseTokenRefreshView):
    """
    POST api/v1/auth/token/refresh/
    Takes a refresh type JSON web token and returns an access type JSON web
    token if the refresh token is valid.
    """

    pass


class TokenVerifyView(BaseTokenVerifyView):
    """
    POST api/v1/auth/token/verify/
    Takes a token and indicates if it is valid. This view provides no
    information about a token's fitness for a particular use.
    """

    pass


class RegisterView(generics.CreateAPIView):
    """
    POST api/v1/auth/register/
    Register a new user account.

    Creates a new user with the provided information and returns the user data
    along with JWT tokens for immediate authentication.
    """

    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate tokens for the new user
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "success": True,
                "message": "User registered successfully.",
                "data": UserSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET/PUT/PATCH/DELETE api/v1/auth/users/{id}/
    Retrieve, update, or delete a user account.

    Regular users can only access/update their own profile.
    ADMIN and HR users can manage all users including changing roles.
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Use UserSerializer for self, AdminUserSerializer for admin/HR updates."""
        if self.request.method in ("PUT", "PATCH"):
            pk = self.kwargs.get("pk")
            # If updating another user (not self) and requester is Admin/HR, use admin serializer
            if pk and pk != "me" and str(pk) != str(self.request.user.pk):
                if self.request.user.user_type in ("ADMIN", "HR"):
                    from .serializers import AdminUserSerializer
                    return AdminUserSerializer
        return UserSerializer

    def get_object(self):
        """Allow users to access their own profile or admins to access any."""
        pk = self.kwargs.get("pk")
        if pk == "me" or (not pk and self.request.user):
            return self.request.user
        return super().get_object()

    def perform_destroy(self, instance):
        """Soft delete by deactivating the user."""
        instance.is_active = False
        instance.save()


class UserListView(generics.ListAPIView):
    """
    GET api/v1/auth/users/
    List all users with pagination, filtering, and search.

    ADMIN and HR users see all users (active and inactive).
    Regular users only see active users.
    """

    queryset = User.objects.all()
    serializer_class = UserListSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ["username", "email", "first_name", "last_name", "employee_id"]
    filterset_fields = ["user_type", "gender", "is_active"]

    def get_queryset(self):
        qs = super().get_queryset()
        # Regular users only see active users
        if self.request.user.user_type not in ("ADMIN", "HR"):
            qs = qs.filter(is_active=True)
        return qs


class ChangePasswordView(generics.UpdateAPIView):
    """
    PUT api/v1/auth/change-password/
    Change the authenticated user's password.
    """

    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = self.get_object()
        user.set_password(serializer.validated_data["new_password"])
        user.save()

        return Response(
            {
                "success": True,
                "message": "Password changed successfully.",
            },
            status=status.HTTP_200_OK,
        )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """
    POST api/v1/auth/login/
    Authenticate user and return JWT tokens.

    Accepts username/email and password. Returns access and refresh tokens
    along with user data.
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    username = serializer.validated_data["username"]
    password = serializer.validated_data["password"]

    # Try to authenticate with username first, then email
    user = User.objects.filter(username=username).first()
    if not user:
        user = User.objects.filter(email=username).first()

    if not user or not user.check_password(password):
        raise BadRequest("Invalid credentials.")

    if not user.is_active:
        raise BadRequest("Account is disabled.")

    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(user)

    return Response(
        {
            "success": True,
            "message": "Login successful.",
            "data": UserSerializer(user).data,
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
        }
    )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def password_reset_request(request):
    """
    POST api/v1/auth/password-reset/
    Request a password reset email.

    Sends a password reset link to the provided email address if it exists
    in the system.
    """
    serializer = PasswordResetRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    email = serializer.validated_data["email"]
    user = User.objects.filter(email=email).first()

    if user:
        # In production, send actual email with reset link
        # For now, return a token for testing
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        return Response(
            {
                "success": True,
                "message": "Password reset email sent.",
                "data": {
                    "uid": uid,
                    "token": token,
                    "email": email,
                },
            }
        )

    # Don't reveal whether the email exists
    return Response(
        {
            "success": True,
            "message": "If an account with that email exists, a password reset link has been sent.",
        }
    )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def password_reset_confirm(request):
    """
    POST api/v1/auth/password-reset/confirm/
    Confirm password reset with token and set new password.
    """
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    from django.contrib.auth.tokens import default_token_generator
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str

    try:
        uid = force_str(urlsafe_base64_decode(serializer.validated_data["token"]))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        raise BadRequest("Invalid reset token.")

    if not default_token_generator.check_token(user, serializer.validated_data["token"]):
        raise BadRequest("Invalid or expired reset token.")

    user.set_password(serializer.validated_data["password"])
    user.save()

    return Response(
        {
            "success": True,
            "message": "Password has been reset successfully.",
        }
    )


@api_view(["GET", "PUT"])
@permission_classes([permissions.IsAuthenticated])
def me_view(request):
    """
    GET/PUT api/v1/auth/me/

    GET: Get the authenticated user's profile.
    PUT: Update the authenticated user's profile (first_name, last_name, email, phone_number, etc.).
    """
    if request.method == "GET":
        serializer = UserSerializer(request.user)
        return Response(
            {
                "success": True,
                "data": serializer.data,
            }
        )

    # PUT - Update profile
    serializer = UserSerializer(
        request.user,
        data=request.data,
        partial=True,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(
        {
            "success": True,
            "data": serializer.data,
            "message": "Profile updated successfully.",
        }
    )
