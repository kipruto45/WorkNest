from __future__ import annotations

from django.core.cache import caches
from django.db import connections
from django.db.utils import OperationalError


def get_database_health() -> str:
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return "ok"
    except OperationalError:
        return "unavailable"


def get_cache_health() -> str:
    try:
        cache = caches["default"]
        cache.set("healthcheck", "ok", timeout=5)
        return "ok" if cache.get("healthcheck") == "ok" else "unavailable"
    except Exception:
        return "unavailable"
