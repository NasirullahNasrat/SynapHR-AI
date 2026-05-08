"""
Main URL configuration for SynapHR AI project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import render
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from config.apps.accounts.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

api_v1_patterns = [
    # Authentication
    path("auth/", include("config.apps.accounts.urls")),
    # HRMS Core
    path("hr/", include("config.apps.hrms.urls")),
    # Chatbot
    path("chatbot/", include("config.apps.chatbot.urls")),
    # Notifications
    path("notifications/", include("config.apps.notifications.urls")),
]

# API-only URL patterns (these must be matched before the SPA catch-all)
api_urlpatterns = [
    # Admin
    path("admin/", admin.site.urls),
    # API v1
    path("api/v1/", include(api_v1_patterns)),
    # SimpleJWT endpoints
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    # API Schema & Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/docs/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    # DRF browsable API auth
    path("api-auth/", include("rest_framework.urls")),
]

# Serve media files in development
if settings.DEBUG:
    api_urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# ---------------------------------------------------------------------------
# SPA (Single Page Application) serving via Django templates/static
# ---------------------------------------------------------------------------
def _spa_index(request):
    """Serve index.html for SPA client-side routing via Django templates."""
    return render(request, "index.html")


urlpatterns = api_urlpatterns + [
    # SPA catch-all: serve index.html for all non-API, non-admin routes (client-side routing)
    re_path(r"^(?!api/|admin/|api-auth/).*$", _spa_index, name="spa-index"),
]
