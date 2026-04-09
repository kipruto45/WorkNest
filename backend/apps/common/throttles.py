from __future__ import annotations

import logging

from django.core.cache import InvalidCacheBackendError, caches
from rest_framework.throttling import AnonRateThrottle as DRFAnonRateThrottle
from rest_framework.throttling import UserRateThrottle as DRFUserRateThrottle

logger = logging.getLogger(__name__)


class CacheAliasRateThrottleMixin:
    cache_alias = "throttle"

    def __init__(self, *args, **kwargs):
        self.cache = self._resolve_cache()
        super().__init__(*args, **kwargs)

    def _resolve_cache(self):
        try:
            return caches[self.cache_alias]
        except InvalidCacheBackendError:
            logger.warning("throttle_cache_alias_missing", extra={"cache_alias": self.cache_alias})
            return caches["default"]

    def allow_request(self, request, view):
        try:
            return super().allow_request(request, view)
        except Exception:
            logger.exception(
                "throttle_cache_unavailable",
                extra={"cache_alias": self.cache_alias, "scope": getattr(self, "scope", None)},
            )
            return True


class AnonRateThrottle(CacheAliasRateThrottleMixin, DRFAnonRateThrottle):
    pass


class UserRateThrottle(CacheAliasRateThrottleMixin, DRFUserRateThrottle):
    pass
