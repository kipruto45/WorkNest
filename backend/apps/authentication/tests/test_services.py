from django.contrib.auth import get_user_model
from django.core import mail
from django.test import RequestFactory, TestCase, override_settings
from unittest.mock import patch

from apps.authentication.adapter import find_or_create_google_user
from apps.authentication.google_service import get_or_create_google_user
from apps.authentication.services import create_user_account, request_password_reset, sync_google_account_profile
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

    @override_settings(WELCOME_EMAIL_ENABLED=True)
    def test_create_user_account_queues_welcome_email(self) -> None:
        create_user_account(
            email="welcome@example.com",
            password="StrongPass123!",
            name="Welcome User",
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Welcome to", mail.outbox[0].subject)

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

    @override_settings(
        FRONTEND_URL="http://localhost:5173",
        PASSWORD_RESET_LINK_BASE_URL="https://work-nest-lemon.vercel.app/reset-password",
    )
    def test_request_password_reset_prefers_public_reset_url(self) -> None:
        user = User.objects.create_user(
            email="jane-public@example.com",
            password="StrongPass123!",
            name="Jane Public",
        )
        request = RequestFactory().post("/api/v1/auth/password-reset/")

        request_password_reset(email=user.email, request=request)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("https://work-nest-lemon.vercel.app/reset-password", mail.outbox[0].body)
        self.assertNotIn("http://localhost:5173/reset-password", mail.outbox[0].body)

    @override_settings(
        ENVIRONMENT="production",
        FRONTEND_URL="http://localhost:5173",
        PASSWORD_RESET_LINK_BASE_URL="",
        PUBLIC_WEBAPP_URL="",
    )
    def test_request_password_reset_uses_default_public_webapp_url_in_production(self) -> None:
        user = User.objects.create_user(
            email="jane-default-public@example.com",
            password="StrongPass123!",
            name="Jane Public Default",
        )
        request = RequestFactory().post("/api/v1/auth/password-reset/")

        request_password_reset(email=user.email, request=request)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("https://work-nest-lemon.vercel.app/reset-password", mail.outbox[0].body)
        self.assertNotIn("http://localhost:5173/reset-password", mail.outbox[0].body)

    def test_request_password_reset_does_not_error_for_unknown_email(self) -> None:
        request = RequestFactory().post("/api/v1/auth/password-reset/")

        request_password_reset(email="unknown@example.com", request=request)

        self.assertEqual(len(mail.outbox), 0)

    @patch("apps.authentication.services.send_password_reset_email", side_effect=RuntimeError("smtp offline"))
    def test_request_password_reset_swallows_internal_email_failures(self, mocked_send_password_reset_email) -> None:
        user = User.objects.create_user(
            email="resilient@example.com",
            password="StrongPass123!",
            name="Resilient User",
        )
        request = RequestFactory().post("/api/v1/auth/password-reset/")

        request_password_reset(email=user.email, request=request)

        mocked_send_password_reset_email.assert_called_once()
        self.assertEqual(len(mail.outbox), 0)

    def test_sync_google_account_profile_fills_missing_details(self) -> None:
        user = User.objects.create_user(
            email="google-user@example.com",
            password="StrongPass123!",
            name="google-user",
            auth_provider=User.AuthProvider.EMAIL,
            email_verified=False,
        )

        sync_google_account_profile(
            user=user,
            name="Google User",
            first_name="Google",
            last_name="User",
            avatar="https://example.com/avatar.png",
            email_verified=True,
        )

        user.refresh_from_db()

        self.assertEqual(user.auth_provider, User.AuthProvider.GOOGLE)
        self.assertTrue(user.email_verified)
        self.assertEqual(user.first_name, "Google")
        self.assertEqual(user.last_name, "User")
        self.assertEqual(user.avatar, "https://example.com/avatar.png")

    def test_find_or_create_google_user_persists_avatar_for_new_users(self) -> None:
        user = find_or_create_google_user(
            "new-google@example.com",
            "New",
            "Google",
            "New Google",
            "https://example.com/new-google.png",
        )

        self.assertEqual(user.auth_provider, User.AuthProvider.GOOGLE)
        self.assertEqual(user.avatar, "https://example.com/new-google.png")
        self.assertEqual(user.first_name, "New")
        self.assertEqual(user.last_name, "Google")

    def test_get_or_create_google_user_repairs_existing_google_profile(self) -> None:
        user = User.objects.create_user(
            email="existing-google@example.com",
            password="StrongPass123!",
            name="existing-google",
            auth_provider=User.AuthProvider.GOOGLE,
            email_verified=False,
            first_name="",
            last_name="",
            avatar="",
        )

        result_user, is_new = get_or_create_google_user(
            {
                "email": user.email,
                "email_verified": True,
                "name": "Existing Google",
                "first_name": "Existing",
                "last_name": "Google",
                "avatar": "https://example.com/existing-google.png",
                "google_sub": "sub-123",
            },
            account_type=User.AccountType.PERSONAL,
        )

        user.refresh_from_db()

        self.assertFalse(is_new)
        self.assertEqual(str(result_user.id), str(user.id))
        self.assertTrue(user.email_verified)
        self.assertEqual(user.first_name, "Existing")
        self.assertEqual(user.last_name, "Google")
        self.assertEqual(user.avatar, "https://example.com/existing-google.png")
