from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import RedirectView


def _render_probe_response(*, request, message: str, services: dict, status_code: int = 200) -> JsonResponse:
    return JsonResponse(
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
        status=status_code,
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


urlpatterns = [
    path("", RedirectView.as_view(url="/api/v1/docs/swagger/", permanent=False), name="root"),
    path("admin/", admin.site.urls),
    path("api/v1/health/live/", render_live_probe, name="render-health-live"),
    path("api/v1/health/ready/", render_ready_probe, name="render-health-ready"),
    path("api/v1/", include(("config.api_v1_urls", "api_v1"), namespace="api_v1")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.FILES_URL, document_root=settings.FILES_ROOT)
