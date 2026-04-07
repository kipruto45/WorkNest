from __future__ import annotations

from django.conf import settings

from apps.common.validators import parse_bool


def get_api_version() -> str:
    return getattr(settings, "API_VERSION", "v1")


def get_runtime_environment() -> str:
    return getattr(settings, "ENVIRONMENT", "local")


def build_paginated_payload(*, paginator, serializer_data) -> dict:
    return {
        "count": paginator.page.paginator.count,
        "next": paginator.get_next_link(),
        "previous": paginator.get_previous_link(),
        "results": serializer_data,
    }


def coerce_bool_query_param(value):
    return parse_bool(value)
