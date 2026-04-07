from django.test import TestCase
from django.urls import reverse


class RequestIDMiddlewareTests(TestCase):
    def test_request_id_header_is_echoed_back(self) -> None:
        response = self.client.get(reverse("api_v1:common:healthcheck"), HTTP_X_REQUEST_ID="frontend-req-123")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Request-ID"], "frontend-req-123")
        self.assertEqual(response.json()["request_id"], "frontend-req-123")
