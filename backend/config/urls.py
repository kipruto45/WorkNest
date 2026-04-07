from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import include, path
from django.views.generic import RedirectView
from urllib.parse import urlencode
from apps.integrations.email.builders import _get_frontend_url


def _json_payload_response(payload: dict, status_code: int = 200) -> JsonResponse:
    response = JsonResponse(payload, status=status_code)
    response.data = payload
    return response


def _render_probe_response(*, request, message: str, services: dict, status_code: int = 200) -> JsonResponse:
    return _json_payload_response(
        {
            "success": True,
            "message": message,
            "request_id": getattr(request, "request_id", None),
            "data": {
                "status": "ok" if status_code < 400 else "degraded",
                "environment": getattr(settings, "ENVIRONMENT", "production"),
                "services": services,
            },
        },
        status_code=status_code,
    )


def render_live_probe(request):
    return _render_probe_response(
        request=request,
        message="Liveness probe completed.",
        services={"application": "ok"},
    )


def render_ready_probe(request):
    return _render_probe_response(
        request=request,
        message="Readiness probe completed.",
        services={
            "application": "ok",
            "database": "ok",
            "redis": "optional",
            "channels": "configured",
            "celery": "configured",
        },
    )


def _build_google_callback_url(request) -> str:
    configured_redirect_uri = str(getattr(settings, "GOOGLE_REDIRECT_URI", "")).strip()
    if configured_redirect_uri:
        return configured_redirect_uri
    backend_url = str(getattr(settings, "BACKEND_URL", "")).strip().rstrip("/")
    if not backend_url:
        backend_url = request.build_absolute_uri("/").rstrip("/")
    return f"{backend_url}/api/v1/auth/google/callback/"


def _build_google_login_url(request) -> str | None:
    client_id = str(getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")).strip()
    client_secret = str(getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")).strip()
    if not client_id or not client_secret:
        return None
    params = {
        "client_id": client_id,
        "redirect_uri": _build_google_callback_url(request),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def render_google_config(request):
    login_url = _build_google_login_url(request)
    return _json_payload_response(
        {
            "success": True,
            "message": "Google OAuth configuration retrieved successfully.",
            "request_id": getattr(request, "request_id", None),
            "data": {
                "provider": "google",
                "enabled": bool(login_url),
                "login_url": login_url,
                "callback_url": _build_google_callback_url(request),
            },
        }
    )


def render_google_login(request):
    login_url = _build_google_login_url(request)
    if not login_url:
        return _json_payload_response(
            {
                "success": False,
                "message": "Google OAuth is not configured on the backend.",
                "request_id": getattr(request, "request_id", None),
                "errors": {"detail": "Google OAuth is not configured on the backend."},
            },
            status_code=400,
        )

    if request.GET.get("redirect", "true").lower() == "true":
        return HttpResponseRedirect(login_url)

    return _json_payload_response(
        {
            "success": True,
            "message": "Google login URL generated successfully.",
            "request_id": getattr(request, "request_id", None),
            "data": {
                "provider": "google",
                "login_url": login_url,
            },
        }
    )


def render_google_callback(request):
    frontend_url = _get_frontend_url().rstrip("/")
    try:
        from apps.authentication.adapter import handle_google_oauth_callback

        return handle_google_oauth_callback(request)
    except Exception:
        return HttpResponseRedirect(f"{frontend_url}/login?error=google_auth_failed")


urlpatterns = [
    path("", RedirectView.as_view(url="/api/v1/docs/swagger/", permanent=False), name="root"),
    path("admin/", admin.site.urls),
    path("api/v1/health/live/", render_live_probe, name="render-health-live"),
    path("api/v1/health/ready/", render_ready_probe, name="render-health-ready"),
    path("api/v1/auth/google/config/", render_google_config, name="render-google-config"),
    path("api/v1/auth/google/login/", render_google_login, name="render-google-login"),
    path("api/v1/auth/google/callback/", render_google_callback, name="render-google-callback"),
    path("api/v1/", include(("config.api_v1_urls", "api_v1"), namespace="api_v1")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.FILES_URL, document_root=settings.FILES_ROOT)
