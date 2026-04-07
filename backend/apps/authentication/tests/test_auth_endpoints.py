from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
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
