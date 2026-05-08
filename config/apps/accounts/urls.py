"""
URL configuration for the accounts app.
"""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    # Registration & Login
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.login_view, name="login"),
    # Profile
    path("me/", views.me_view, name="me"),
    path("users/", views.UserListView.as_view(), name="user-list"),
    path("users/<str:pk>/", views.UserDetailView.as_view(), name="user-detail"),
    # Password Management
    path("change-password/", views.ChangePasswordView.as_view(), name="change-password"),
    path("password-reset/", views.password_reset_request, name="password-reset-request"),
    path("password-reset/confirm/", views.password_reset_confirm, name="password-reset-confirm"),
]
