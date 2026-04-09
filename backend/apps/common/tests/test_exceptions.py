from __future__ import annotations

from django.test import RequestFactory, SimpleTestCase, override_settings
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError

from apps.common.exceptions import ConflictError, ServiceUnavailableError, custom_exception_handler


class CommonExceptionTests(SimpleTestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.request = self.factory.get("/api/v1/test/")
        self.request.request_id = "req-456"

    def test_custom_exception_handler_formats_validation_errors(self) -> None:
        response = custom_exception_handler(ValidationError({"field": ["Required"]}), {"request": self.request})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["errors"]["field"], ["Required"])

    def test_custom_exception_handler_supports_conflict_error(self) -> None:
        response = custom_exception_handler(ConflictError("Already exists"), {"request": self.request})

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["message"], "Request could not be completed due to a conflict.")

    @override_settings(DEBUG=False)
    def test_custom_exception_handler_hides_internal_error_details(self) -> None:
        response = custom_exception_handler(RuntimeError("secret failure"), {"request": self.request})

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["message"], "Server error while processing request.")
        self.assertEqual(response.data["errors"]["detail"], "Internal server error.")

    def test_custom_exception_handler_maps_invalid_tokens_to_session_expired_message(self) -> None:
        response = custom_exception_handler(
            AuthenticationFailed({"detail": "Given token not valid for any token type"}),
            {"request": self.request},
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["message"], "Your session expired. Please log in again.")

    def test_custom_exception_handler_preserves_auth_failure_message(self) -> None:
        response = custom_exception_handler(
            AuthenticationFailed("Invalid email or password."),
            {"request": self.request},
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data["message"], "Invalid email or password.")

    def test_service_unavailable_error_exposes_status_code(self) -> None:
        response = custom_exception_handler(ServiceUnavailableError("Down"), {"request": self.request})

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
