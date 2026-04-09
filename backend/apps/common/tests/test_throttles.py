from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.cache import caches
from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.common.throttles import AnonRateThrottle


class CommonThrottleTests(SimpleTestCase):
    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "test-default-cache",
            },
            "throttle": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "test-throttle-cache",
            },
        }
    )
    def test_throttle_uses_dedicated_cache_alias(self) -> None:
        throttle = AnonRateThrottle()

        self.assertIs(throttle.cache, caches["throttle"])

    def test_throttle_allows_request_when_cache_backend_errors(self) -> None:
        throttle = AnonRateThrottle()
        request = RequestFactory().get("/api/v1/health/ready/")
        request.user = AnonymousUser()

        with patch.object(throttle.cache, "get", side_effect=RuntimeError("redis offline")):
            self.assertTrue(throttle.allow_request(request, view=None))
