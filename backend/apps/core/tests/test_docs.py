from django.test import TestCase
from django.urls import reverse


class DocumentationEndpointsTests(TestCase):
    def test_schema_endpoint_is_available(self) -> None:
        response = self.client.get(
            reverse("api_v1:schema"),
            HTTP_ACCEPT="application/vnd.oai.openapi+json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("openapi", response.content.decode())
