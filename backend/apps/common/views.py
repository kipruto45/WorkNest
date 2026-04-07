from __future__ import annotations

from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.views import APIView

from apps.common.constants import API_NAME, HEALTH_STATUS_DEGRADED, HEALTH_STATUS_OK
from apps.common.health import get_cache_health, get_database_health
from apps.common.responses import success_response
from apps.common.utils import get_api_version, get_runtime_environment


class APIRootView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses=inline_serializer(
            name="APIRootResponse",
            fields={
                "name": serializers.CharField(),
                "version": serializers.CharField(),
                "environment": serializers.CharField(),
                "docs": serializers.DictField(child=serializers.URLField()),
                "system": serializers.DictField(child=serializers.URLField()),
            },
        )
    )
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        return success_response(
            request=request,
            message="API root loaded successfully.",
            data={
                "name": API_NAME,
                "version": get_api_version(),
                "environment": get_runtime_environment(),
                "docs": {
                    "schema": request.build_absolute_uri("/api/v1/schema/"),
                    "swagger": request.build_absolute_uri("/api/v1/docs/"),
                    "redoc": request.build_absolute_uri("/api/v1/docs/redoc/"),
                },
                "system": {
                    "health": request.build_absolute_uri("/api/v1/health/"),
                    "health_live": request.build_absolute_uri("/api/v1/health/live/"),
                    "health_ready": request.build_absolute_uri("/api/v1/health/ready/"),
                    "info": request.build_absolute_uri("/api/v1/system/info/"),
                },
            },
        )


class HealthCheckView(APIView):
    permission_classes = [permissions.AllowAny]

    @staticmethod
    def _build_dependency_snapshot() -> tuple[str, str]:
        try:
            database_status = get_database_health()
        except Exception:
            database_status = "unavailable"

        try:
            cache_status = get_cache_health()
        except Exception:
            cache_status = "unavailable"

        return database_status, cache_status

    @extend_schema(
        responses=inline_serializer(
            name="HealthCheckResponse",
            fields={
                "status": serializers.CharField(),
                "environment": serializers.CharField(),
                "services": serializers.DictField(child=serializers.CharField()),
            },
        )
    )
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        probe = kwargs.get("probe", "full")
        if probe == "live":
            return success_response(
                request=request,
                message="Liveness probe completed.",
                data={
                    "status": HEALTH_STATUS_OK,
                    "environment": get_runtime_environment(),
                    "services": {
                        "application": "ok",
                    },
                },
            )

        database_status, cache_status = self._build_dependency_snapshot()
        response_status = (
            status.HTTP_200_OK
            if database_status == "ok" and cache_status == "ok"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        return success_response(
            request=request,
            message="Readiness probe completed." if probe == "ready" else "Healthcheck completed.",
            data={
                "status": HEALTH_STATUS_OK if response_status == status.HTTP_200_OK else HEALTH_STATUS_DEGRADED,
                "environment": get_runtime_environment(),
                "services": {
                    "database": database_status,
                    "redis": cache_status,
                    "channels": "configured",
                    "celery": "configured",
                },
            },
            status_code=response_status,
        )


class SystemInfoView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses=inline_serializer(
            name="SystemInfoResponse",
            fields={
                "version": serializers.CharField(),
                "environment": serializers.CharField(),
                "debug": serializers.BooleanField(),
                "docs_enabled": serializers.BooleanField(),
            },
        )
    )
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        return success_response(
            request=request,
            message="System information retrieved successfully.",
            data={
                "version": get_api_version(),
                "environment": get_runtime_environment(),
                "debug": settings.DEBUG,
                "docs_enabled": True,
            },
        )
