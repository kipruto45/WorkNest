from django.test import TestCase
from django.urls import reverse


class SystemInfoViewTests(TestCase):
    def test_system_info_returns_runtime_metadata(self) -> None:
        response = self.client.get(reverse("api_v1:common:system-info"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["data"]["version"], "v1")
