from __future__ import annotations

from django.test import RequestFactory, SimpleTestCase

from apps.common.responses import error_response, success_response


class ResponseHelperTests(SimpleTestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.request = self.factory.get("/api/v1/test/")
        self.request.request_id = "req-123"

    def test_success_response_includes_request_id(self) -> None:
        response = success_response(request=self.request, message="ok", data={"hello": "world"})

        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["request_id"], "req-123")
        self.assertEqual(response.data["data"]["hello"], "world")

    def test_error_response_includes_errors(self) -> None:
        response = error_response(request=self.request, message="bad", errors={"field": ["Required"]}, status_code=422)

        self.assertFalse(response.data["success"])
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["errors"]["field"], ["Required"])
