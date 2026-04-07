from django.contrib.auth import get_user_model
from django.core import mail
from django.test import RequestFactory, TestCase, override_settings

from apps.authentication.services import create_user_account, request_password_reset
from apps.users.models import User

User = get_user_model()


class AuthenticationServiceTests(TestCase):
    def test_create_user_account_sets_default_provider(self) -> None:
        user = create_user_account(
            email="jane@example.com",
            password="StrongPass123!",
            name="Jane Doe",
        )

        self.assertEqual(user.auth_provider, User.AuthProvider.EMAIL)
        self.assertFalse(user.email_verified)

    @override_settings(FRONTEND_URL="http://localhost:5173")
    def test_request_password_reset_sends_email_for_active_user(self) -> None:
        user = User.objects.create_user(
            email="jane@example.com",
            password="StrongPass123!",
            name="Jane Doe",
        )
        request = RequestFactory().post("/api/v1/auth/password-reset/")

        request_password_reset(email=user.email, request=request)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(user.email, mail.outbox[0].to)

    def test_request_password_reset_does_not_error_for_unknown_email(self) -> None:
        request = RequestFactory().post("/api/v1/auth/password-reset/")

        request_password_reset(email="unknown@example.com", request=request)

        self.assertEqual(len(mail.outbox), 0)
