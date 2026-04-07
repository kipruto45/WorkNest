from django.urls import path

from apps.common.views import HealthCheckView, SystemInfoView

app_name = "common"

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="healthcheck"),
    path("health/live/", HealthCheckView.as_view(), {"probe": "live"}, name="health-live"),
    path("health/ready/", HealthCheckView.as_view(), {"probe": "ready"}, name="health-ready"),
    path("system/info/", SystemInfoView.as_view(), name="system-info"),
]
