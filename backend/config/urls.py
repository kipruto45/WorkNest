from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import include, path
from django.views.generic import RedirectView
from urllib.parse import urlencode

from apps.authentication.adapter import build_google_oauth_state
from apps.common.views import HealthCheckView
from apps.integrations.email.builders import _get_frontend_url


def _json_payload_response(payload: dict, status_code: int = 200) -> JsonResponse:
    response = JsonResponse(payload, status=status_code)
    response.data = payload
    return response


def _build_google_callback_url(request) -> str:
    configured_redirect_uri = str(getattr(settings, "GOOGLE_REDIRECT_URI", "")).strip()
    if configured_redirect_uri:
        return configured_redirect_uri
    backend_url = str(getattr(settings, "BACKEND_URL", "")).strip().rstrip("/")
    if not backend_url:
        backend_url = request.build_absolute_uri("/").rstrip("/")
    return f"{backend_url}/api/v1/auth/google/callback/"


def _normalize_frontend_next_path(next_path: str | None) -> str:
    candidate = str(next_path or "").strip()
    if not candidate.startswith("/"):
        return ""
    if candidate.startswith("//"):
        return ""
    return candidate


def _build_google_login_url(request, *, next_path: str = "", account_type: str = "", flow: str = "login", team_name: str = "") -> str | None:
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
    state = build_google_oauth_state(
        next_path=_normalize_frontend_next_path(next_path),
        account_type=account_type,
        flow=flow,
        team_name=team_name,
    )
    if state:
        params["state"] = state
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def render_google_config(request):
    login_url = _build_google_login_url(
        request,
        next_path=request.GET.get("next"),
        account_type=str(request.GET.get("account_type", "")).strip(),
        flow=str(request.GET.get("flow", "login")).strip() or "login",
        team_name=str(request.GET.get("team_name", "")).strip(),
    )
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
    account_type = str(request.GET.get("account_type", "")).strip()
    flow = str(request.GET.get("flow", "login")).strip() or "login"
    team_name = str(request.GET.get("team_name", "")).strip()
    valid_account_types = {"personal", "team"}
    if flow not in {"login", "register"}:
        flow = "login"

    if flow == "register" and account_type not in valid_account_types:
        return _json_payload_response(
            {
                "success": False,
                "message": "Choose your workspace mode before continuing with Google.",
                "request_id": getattr(request, "request_id", None),
                "errors": {"account_type": "Choose your workspace mode before continuing with Google."},
            },
            status_code=400,
        )
    if flow == "login" and account_type not in valid_account_types:
        account_type = ""

    login_url = _build_google_login_url(
        request,
        next_path=request.GET.get("next"),
        account_type=account_type,
        flow=flow,
        team_name=team_name,
    )
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
    path("api/v1/health/live/", HealthCheckView.as_view(), {"probe": "live"}, name="render-health-live"),
    path("api/v1/health/ready/", HealthCheckView.as_view(), {"probe": "ready"}, name="render-health-ready"),
    path("api/v1/auth/google/config/", render_google_config, name="render-google-config"),
    path("api/v1/auth/google/login/", render_google_login, name="render-google-login"),
    path("api/v1/auth/google/callback/", render_google_callback, name="render-google-callback"),
    path("api/v1/", include(("config.api_v1_urls", "api_v1"), namespace="api_v1")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.FILES_URL, document_root=settings.FILES_ROOT)
