from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from apps.common.views import HealthCheckView


urlpatterns = [
    path("", RedirectView.as_view(url="/api/v1/docs/swagger/", permanent=False), name="root"),
    path("admin/", admin.site.urls),
    path("api/v1/health/live/", HealthCheckView.as_view(), {"probe": "live"}, name="render-health-live"),
    path("api/v1/health/ready/", HealthCheckView.as_view(), {"probe": "ready"}, name="render-health-ready"),
    path("api/v1/", include(("config.api_v1_urls", "api_v1"), namespace="api_v1")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.FILES_URL, document_root=settings.FILES_ROOT)
