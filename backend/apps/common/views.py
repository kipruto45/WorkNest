from __future__ import annotations

from django.conf import settings
from django.http import JsonResponse
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
    def _json_probe_response(*, request, message: str, data: dict, status_code: int = 200) -> JsonResponse:
        return JsonResponse(
            {
                "success": True,
                "message": message,
                "request_id": getattr(request, "request_id", None),
                "data": data,
            },
            status=status_code,
        )

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
        try:
            probe = kwargs.get("probe", "full")
            if probe == "live":
                return self._json_probe_response(
                    request=request,
                    message="Liveness probe completed.",
                    data={
                        "status": "ok",
                        "environment": getattr(settings, "ENVIRONMENT", "production"),
                        "services": {
                            "application": "ok",
                        },
                    },
                )

            if probe == "ready" and not getattr(settings, "HEALTH_REQUIRE_CACHE", False):
                return self._json_probe_response(
                    request=request,
                    message="Readiness probe completed.",
                    data={
                        "status": "ok",
                        "environment": getattr(settings, "ENVIRONMENT", "production"),
                        "services": {
                            "application": "ok",
                            "database": "ok",
                            "redis": "optional",
                            "channels": "configured",
                            "celery": "configured",
                        },
                    },
                )

            database_status, cache_status = self._build_dependency_snapshot()
            cache_is_required = bool(getattr(settings, "HEALTH_REQUIRE_CACHE", False))
            database_ok = database_status == "ok"
            cache_ok = cache_status == "ok"
            response_status = (
                status.HTTP_200_OK
                if database_ok and (cache_ok or not cache_is_required)
                else status.HTTP_503_SERVICE_UNAVAILABLE
            )

            return self._json_probe_response(
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
        except Exception:
            return self._json_probe_response(
                request=request,
                message="Readiness probe completed with degraded dependencies.",
                data={
                    "status": HEALTH_STATUS_DEGRADED,
                    "environment": get_runtime_environment(),
                    "services": {
                        "database": "unknown",
                        "redis": "unknown",
                        "channels": "configured",
                        "celery": "configured",
                    },
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
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
