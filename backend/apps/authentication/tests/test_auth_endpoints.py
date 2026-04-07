from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APITestCase

from apps.integrations.models import EmailDelivery
from apps.authentication.models import LoginActivity

User = get_user_model()


class AuthenticationEndpointTests(APITestCase):
    def test_register_returns_tokens_and_sets_cookie(self) -> None:
        response = self.client.post(
            reverse("api_v1:authentication:register"),
            {
                "name": "Jane Doe",
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data["data"]["tokens"])
        self.assertIn("refresh", response.data["data"]["tokens"])
        self.assertEqual(response.data["data"]["user"]["email"], "jane@example.com")
        self.assertIn("refresh_token", response.cookies)

    def test_register_rejects_duplicate_email(self) -> None:
        User.objects.create_user(email="jane@example.com", password="StrongPass123!", name="Jane Doe")

        response = self.client.post(
            reverse("api_v1:authentication:register"),
            {
                "name": "Jane Duplicate",
                "email": "jane@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("email", response.data["errors"])

    def test_login_returns_access_token_and_records_activity(self) -> None:
        user = User.objects.create_user(
            email="jane@example.com",
            password="StrongPass123!",
            name="Jane Doe",
        )

        response = self.client.post(
            reverse("api_v1:authentication:login"),
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data["data"]["tokens"])
        self.assertIn("refresh", response.data["data"]["tokens"])
        self.assertEqual(LoginActivity.objects.filter(user=user, success=True).count(), 1)
        user.refresh_from_db()
        self.assertIsNotNone(user.last_login)

    def test_login_rejects_invalid_credentials(self) -> None:
        User.objects.create_user(
            email="jane@example.com",
            password="StrongPass123!",
            name="Jane Doe",
        )

        response = self.client.post(
            reverse("api_v1:authentication:login"),
            {"email": "jane@example.com", "password": "wrong-pass"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data["success"])
        self.assertEqual(LoginActivity.objects.filter(success=False).count(), 1)

    def test_login_accepts_case_insensitive_email(self) -> None:
        user = User.objects.create_user(
            email="jane@example.com",
            password="StrongPass123!",
            name="Jane Doe",
        )

        response = self.client.post(
            reverse("api_v1:authentication:login"),
            {"email": "Jane@Example.com", "password": "StrongPass123!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(LoginActivity.objects.filter(user=user, success=True).count(), 1)

    @patch("apps.authentication.services.queue_welcome_email", side_effect=RuntimeError("smtp unavailable"))
    def test_register_succeeds_when_welcome_email_queueing_fails(self, _mock_queue_welcome_email) -> None:
        response = self.client.post(
            reverse("api_v1:authentication:register"),
            {
                "name": "Jane Doe",
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane-welcome@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertTrue(User.objects.filter(email="jane-welcome@example.com").exists())

    @patch("apps.authentication.views.CurrentUserSerializer", side_effect=RuntimeError("serializer unavailable"))
    def test_register_succeeds_when_current_user_serialization_fails(self, _mock_serializer) -> None:
        response = self.client.post(
            reverse("api_v1:authentication:register"),
            {
                "name": "Jane Serializer",
                "email": "jane-serializer@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["user"]["email"], "jane-serializer@example.com")
        self.assertIn("auth_provider", response.data["data"]["user"])

    def test_register_succeeds_with_invalid_forwarded_for_header(self) -> None:
        response = self.client.post(
            reverse("api_v1:authentication:register"),
            {
                "name": "Jane Doe",
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane-proxy@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            },
            format="json",
            HTTP_X_FORWARDED_FOR="unknown, 203.0.113.42",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="jane-proxy@example.com")
        self.assertEqual(LoginActivity.objects.filter(user=user).count(), 0)

    def test_login_succeeds_with_invalid_forwarded_for_header(self) -> None:
        user = User.objects.create_user(
            email="jane-proxy@example.com",
            password="StrongPass123!",
            name="Jane Doe",
        )

        response = self.client.post(
            reverse("api_v1:authentication:login"),
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
            HTTP_X_FORWARDED_FOR="unknown, 203.0.113.42",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        login_activity = LoginActivity.objects.get(user=user, success=True)
        self.assertEqual(login_activity.ip_address, "203.0.113.42")

    @patch("apps.authentication.views.CurrentUserSerializer", side_effect=RuntimeError("serializer unavailable"))
    def test_login_succeeds_when_current_user_serialization_fails(self, _mock_serializer) -> None:
        user = User.objects.create_user(
            email="jane-login-serializer@example.com",
            password="StrongPass123!",
            name="Jane Doe",
        )

        response = self.client.post(
            reverse("api_v1:authentication:login"),
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["user"]["email"], user.email)
        self.assertIn("auth_provider", response.data["data"]["user"])

    def test_refresh_uses_cookie_when_body_missing(self) -> None:
        user = User.objects.create_user(
            email="jane@example.com",
            password="StrongPass123!",
            name="Jane Doe",
        )
        login_response = self.client.post(
            reverse("api_v1:authentication:login"),
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
        )
        self.client.cookies = login_response.cookies

        response = self.client.post(reverse("api_v1:authentication:token-refresh"), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data["data"]["tokens"])

    def test_refresh_rejects_invalid_token(self) -> None:
        response = self.client.post(
            reverse("api_v1:authentication:token-refresh"),
            {"refresh": "invalid-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_refresh_rejects_blacklisted_token(self) -> None:
        user = User.objects.create_user(
            email="jane@example.com",
            password="StrongPass123!",
            name="Jane Doe",
        )
        login_response = self.client.post(
            reverse("api_v1:authentication:login"),
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
        )
        refresh_token = login_response.data["data"]["tokens"]["refresh"]

        first_refresh = self.client.post(
            reverse("api_v1:authentication:token-refresh"),
            {"refresh": refresh_token},
            format="json",
        )
        second_refresh = self.client.post(
            reverse("api_v1:authentication:token-refresh"),
            {"refresh": refresh_token},
            format="json",
        )

        self.assertEqual(first_refresh.status_code, status.HTTP_200_OK)
        self.assertEqual(second_refresh.status_code, status.HTTP_400_BAD_REQUEST)

    def test_logout_requires_authentication(self) -> None:
        response = self.client.post(reverse("api_v1:authentication:logout"), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_blacklists_refresh_token(self) -> None:
        user = User.objects.create_user(
            email="jane@example.com",
            password="StrongPass123!",
            name="Jane Doe",
        )
        login_response = self.client.post(
            reverse("api_v1:authentication:login"),
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
        )
        access = login_response.data["data"]["tokens"]["access"]
        refresh = login_response.data["data"]["tokens"]["refresh"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        logout_response = self.client.post(
            reverse("api_v1:authentication:logout"),
            {"refresh": refresh},
            format="json",
        )
        refresh_response = self.client.post(
            reverse("api_v1:authentication:token-refresh"),
            {"refresh": refresh},
            format="json",
        )

        self.assertEqual(logout_response.status_code, status.HTTP_205_RESET_CONTENT)
        self.assertEqual(refresh_response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(FRONTEND_URL="http://localhost:5173")
    def test_password_reset_request_sends_email(self) -> None:
        user = User.objects.create_user(
            email="jane@example.com",
            password="StrongPass123!",
            name="Jane Doe",
        )

        response = self.client.post(
            reverse("api_v1:authentication:password-reset-request"),
            {"email": user.email},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset-password", mail.outbox[0].body)
        self.assertTrue(EmailDelivery.objects.filter(email_type="password_reset", recipient_email=user.email).exists())

    def test_password_reset_request_keeps_unknown_email_response_generic(self) -> None:
        response = self.client.post(
            reverse("api_v1:authentication:password-reset-request"),
            {"email": "missing@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "If an account exists for that email, a reset link has been sent.")
        self.assertEqual(len(mail.outbox), 0)

    def test_password_reset_confirm_updates_password(self) -> None:
        user = User.objects.create_user(
            email="jane@example.com",
            password="StrongPass123!",
            name="Jane Doe",
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        response = self.client.post(
            reverse("api_v1:authentication:password-reset-confirm"),
            {
                "uid": uid,
                "token": token,
                "new_password": "EvenStronger456!",
                "new_password_confirm": "EvenStronger456!",
            },
            format="json",
        )

        user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(user.check_password("EvenStronger456!"))

    def test_me_endpoint_requires_authentication(self) -> None:
        response = self.client.get(reverse("api_v1:authentication:me"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_endpoint_returns_authenticated_user(self) -> None:
        user = User.objects.create_user(
            email="jane@example.com",
            password="StrongPass123!",
            name="Jane Doe",
        )
        login_response = self.client.post(
            reverse("api_v1:authentication:login"),
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
        )
        access = login_response.data["data"]["tokens"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = self.client.get(reverse("api_v1:authentication:me"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["email"], user.email)

    def test_google_config_endpoint_is_available(self) -> None:
        response = self.client.get(reverse("api_v1:authentication:google-config"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["provider"], "google")

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="client", GOOGLE_OAUTH_CLIENT_SECRET="secret")
    def test_google_login_endpoint_redirects_when_configured(self) -> None:
        response = self.client.get(reverse("api_v1:authentication:google-login"))

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("accounts.google.com", response["Location"])
        self.assertIn("accounts.google.com", response["Location"])
        self.assertIn("redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fv1%2Fauth%2Fgoogle%2Fcallback%2F", response["Location"])

    @patch("apps.authentication.google_service.authenticate_google_user")
    def test_google_auth_endpoint_returns_full_current_user_payload(self, authenticate_google_user_mock) -> None:
        user = User.objects.create_user(
            email="google-user@example.com",
            password="StrongPass123!",
            name="Google User",
            auth_provider=User.AuthProvider.GOOGLE,
            email_verified=True,
            first_name="Google",
            last_name="User",
            bio="Synced from Google",
        )
        authenticate_google_user_mock.return_value = {
            "user": user,
            "tokens": {
                "access": "access-token",
                "refresh": "refresh-token",
                "refresh_expires_in": 3600,
                "token_type": "Bearer",
            },
            "is_new_user": False,
        }

        response = self.client.post(
            reverse("api_v1:authentication:google-auth"),
            {"credential": "fake-google-id-token"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["user"]["email"], user.email)
        self.assertEqual(response.data["data"]["user"]["auth_provider"], User.AuthProvider.GOOGLE)
        self.assertEqual(response.data["data"]["user"]["bio"], "Synced from Google")
