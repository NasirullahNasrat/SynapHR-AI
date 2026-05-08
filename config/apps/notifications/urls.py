"""
URL configuration for the Notifications app.
"""

from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("ws-token/", views.websocket_token, name="ws-token"),
    path("preferences/", views.notification_preferences, name="preferences"),
]
