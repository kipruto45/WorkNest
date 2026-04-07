from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse


class HealthCheckViewTests(TestCase):
    def test_healthcheck_returns_service_status(self) -> None:
        response = self.client.get(reverse("api_v1:common:healthcheck"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["data"]["status"], "ok")
        self.assertEqual(response.json()["data"]["services"]["database"], "ok")
        self.assertIn("request_id", response.json())
        self.assertIn("X-Request-ID", response)

    def test_liveness_probe_returns_application_status(self) -> None:
        response = self.client.get(reverse("api_v1:common:health-live"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["services"]["application"], "ok")

    def test_readiness_probe_returns_dependency_statuses(self) -> None:
        response = self.client.get(reverse("api_v1:common:health-ready"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["services"]["database"], "ok")
        self.assertEqual(response.json()["data"]["services"]["redis"], "ok")

    @patch("apps.common.views.get_cache_health", side_effect=RuntimeError("redis boot failure"))
    def test_readiness_probe_degrades_when_cache_check_crashes(self, _mock_cache_health) -> None:
        response = self.client.get(reverse("api_v1:common:health-ready"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["data"]["status"], "ok")
        self.assertEqual(response.json()["data"]["services"]["redis"], "unavailable")

    @patch("apps.common.views.HealthCheckView._build_dependency_snapshot", side_effect=RuntimeError("unexpected failure"))
    def test_readiness_probe_returns_structured_fallback_when_probe_logic_crashes(self, _mock_snapshot) -> None:
        response = self.client.get(reverse("api_v1:common:health-ready"))

        self.assertEqual(response.status_code, 503)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["data"]["status"], "degraded")
        self.assertEqual(response.json()["data"]["services"]["database"], "unknown")

    def test_api_root_exposes_versioned_links(self) -> None:
        response = self.client.get(reverse("api_v1:root"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["version"], "v1")
        self.assertIn("/api/v1/health/", response.json()["data"]["system"]["health"])
