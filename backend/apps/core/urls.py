from django.urls import path

from apps.core.views import HealthCheckView, SystemInfoView

app_name = "core"

urlpatterns = [
    path("", HealthCheckView.as_view(), name="healthcheck"),
    path("system/info/", SystemInfoView.as_view(), name="system-info"),
]
