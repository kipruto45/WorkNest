from __future__ import annotations

from django.test import TestCase
from django.urls import reverse


class CommonViewTests(TestCase):
    def test_healthcheck_endpoint_resolves(self) -> None:
        response = self.client.get(reverse("api_v1:common:healthcheck"))

        self.assertIn(response.status_code, {200, 503})
        self.assertIn("status", response.json()["data"])

    def test_system_info_endpoint_returns_common_payload(self) -> None:
        response = self.client.get(reverse("api_v1:common:system-info"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("version", response.json()["data"])
