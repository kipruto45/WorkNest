import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import override_settings
from django.conf import settings
from django.urls import resolve, reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from unittest.mock import patch
from rest_framework import status
from rest_framework.test import APITestCase

from apps.integrations.models import EmailDelivery
from apps.authentication.models import AuthSession, CredentialChangeRequest, EmailVerificationToken, LoginActivity
from apps.authentication.services import confirm_credential_change, register_auth_session, request_email_change
from apps.authentication.tokens import create_token_pair_for_user
from apps.authentication.throttles import LoginThrottle, RegisterThrottle
from apps.common.exceptions import ServiceUnavailableError
from apps.memberships.models import Membership
from apps.teams.models import Team
from apps.teams.services import create_team_with_owner

User = get_user_model()


@override_settings(
    REST_FRAMEWORK={
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_CLASSES": [],
        "DEFAULT_THROTTLE_RATES": {},
    }
)
class AuthenticationEndpointTests(APITestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        RegisterThrottle.rate = "1000/hour"
        LoginThrottle.rate = "1000/hour"

    def test_register_returns_tokens_and_sets_cookie(self) -> None:
        response = self.client.post(
            reverse("api_v1:authentication:register"),
            {
                "name": "Jane Doe",
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane@example.com",
                "phone_number": "+254712345678",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "account_type": "personal",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(response.data["success"])
        self.assertIn("access", response.data["data"]["tokens"])
        self.assertIn("refresh", response.data["data"]["tokens"])
        self.assertEqual(response.data["data"]["user"]["email"], "jane@example.com")
        self.assertIn("refresh_token", response.cookies)

    def test_register_requires_team_name_for_team_accounts(self) -> None:
        response = self.client.post(
            reverse("api_v1:authentication:register"),
            {
                "name": "Team Owner",
                "email": "owner@example.com",
                "phone_number": "+254712345678",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "account_type": "team",
                "team_name": "",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("team_name", response.data["errors"])

    def test_register_team_account_creates_team_and_default_team_id(self) -> None:
        response = self.client.post(
            reverse("api_v1:authentication:register"),
            {
                "name": "Team Owner",
                "email": "team-owner@example.com",
                "phone_number": "+254712345678",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "account_type": "team",
                "team_name": "Alpha Squad",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        user_id = response.data["data"]["user"]["id"]
        self.assertTrue(Team.objects.filter(name="Alpha Squad").exists())
        self.assertTrue(
            Membership.objects.filter(user_id=user_id, role=Membership.Role.ADMIN, status=Membership.Status.ACTIVE).exists()
        )
        self.assertIsNotNone(response.data["data"]["user"]["default_team_id"])

    def test_register_ignores_invalid_bearer_header_on_public_entrypoint(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION="Bearer stale-or-invalid-token")

        response = self.client.post(
            reverse("api_v1:authentication:register"),
            {
                "name": "Fresh User",
                "email": "fresh-user@example.com",
                "phone_number": "+254799000001",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "account_type": "team",
                "team_name": "Fresh Workspace",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data["data"]["user"]["account_type"], "team")

    def test_register_personal_account_creates_personal_team(self) -> None:
        response = self.client.post(
            reverse("api_v1:authentication:register"),
            {
                "name": "Personal Owner",
                "email": "personal-owner@example.com",
                "phone_number": "+254712345678",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "account_type": "personal",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        user_id = response.data["data"]["user"]["id"]
        self.assertTrue(Team.objects.filter(is_personal=True, created_by_id=user_id).exists())
    def test_register_rejects_duplicate_email(self) -> None:
        User.objects.create_user(email="jane@example.com", password="StrongPass123!", name="Jane Doe")

        response = self.client.post(
            reverse("api_v1:authentication:register"),
            {
                "name": "Jane Duplicate",
                "email": "jane@example.com",
                "phone_number": "+254712345678",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "account_type": "personal",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertIn("email", response.data["errors"])

    def test_register_requires_both_email_and_phone_number(self) -> None:
        response = self.client.post(
            reverse("api_v1:authentication:register"),
            {
                "name": "Phone First",
                "email": "phone-first@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "account_type": "personal",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data["errors"])

    def test_register_rejects_duplicate_phone_number_after_normalization(self) -> None:
        User.objects.create_user(phone_number="+254712345678", password="StrongPass123!", name="Phone Owner")

        response = self.client.post(
            reverse("api_v1:authentication:register"),
            {
                "name": "Phone Duplicate",
                "email": "phone-duplicate@example.com",
                "phone_number": "0712345678",
                "phone_country_code": "+254",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "account_type": "personal",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data["errors"])

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

    def test_login_accepts_phone_number_credential(self) -> None:
        user = User.objects.create_user(
            phone_number="+254712345678",
            password="StrongPass123!",
            name="Phone Login",
        )

        response = self.client.post(
            reverse("api_v1:authentication:login"),
            {"credential": "0712345678", "password": "StrongPass123!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["user"]["id"], str(user.id))
        self.assertEqual(LoginActivity.objects.filter(user=user, success=True).count(), 1)

    @patch("apps.authentication.services.queue_credential_change_email")
    def test_login_with_recently_changed_email_prompts_for_updated_details(self, mocked_queue_email) -> None:
        user = User.objects.create_user(
            email="before-change@example.com",
            phone_number="+254712345678",
            password="StrongPass123!",
            name="Change Me",
        )
        request_email_change(user=user, new_email="after-change@example.com", actor=user)
        change_request = CredentialChangeRequest.objects.get(user=user, credential_type="email")
        confirm_credential_change(user=user, credential_type="email", code=change_request.code)

        response = self.client.post(
            reverse("api_v1:authentication:login"),
            {"credential": "before-change@example.com", "password": "StrongPass123!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data["message"],
            "Your email address was recently changed. Sign in with your updated details.",
        )
        mocked_queue_email.assert_called_once()

    def test_current_user_works_after_phone_login(self) -> None:
        user = User.objects.create_user(
            phone_number="+254712345678",
            password="StrongPass123!",
            name="Phone User",
        )

        login_response = self.client.post(
            reverse("api_v1:authentication:login"),
            {"credential": "+254712345678", "password": "StrongPass123!"},
            format="json",
        )
        access = login_response.data["data"]["tokens"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        me_response = self.client.get(reverse("api_v1:authentication:me"))
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["data"]["phone_number"], user.phone_number)

    def test_register_creates_email_verification_token(self) -> None:
        response = self.client.post(
            reverse("api_v1:authentication:register"),
            {
                "name": "Verify Me",
                "email": "verify-me@example.com",
                "phone_number": "+254712345678",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "account_type": "personal",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="verify-me@example.com")
        self.assertFalse(user.email_verified)
        self.assertTrue(EmailVerificationToken.objects.filter(user=user, used_at__isnull=True).exists())

    def test_verify_email_endpoint_marks_user_verified(self) -> None:
        user = User.objects.create_user(
            email="verify-later@example.com",
            password="StrongPass123!",
            name="Verify Later",
            email_verified=False,
        )
        token = EmailVerificationToken.objects.create(
            user=user,
            token="verify-token",
            expires_at=timezone.now() + timedelta(days=1),
        )

        response = self.client.post(
            reverse("api_v1:authentication:email-verification-verify"),
            {"token": token.token},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        token.refresh_from_db()
        self.assertTrue(user.email_verified)
        self.assertIsNotNone(token.used_at)

    def test_login_creates_session_and_user_can_revoke_it(self) -> None:
        user = User.objects.create_user(
            email="session-user@example.com",
            password="StrongPass123!",
            name="Session User",
        )

        login_response = self.client.post(
            reverse("api_v1:authentication:login"),
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
        )

        access = login_response.data["data"]["tokens"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        list_response = self.client.get(reverse("api_v1:authentication:sessions"))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data["data"]), 1)

        session_id = list_response.data["data"][0]["id"]
        revoke_response = self.client.delete(reverse("api_v1:authentication:session-detail", kwargs={"pk": session_id}))
        self.assertEqual(revoke_response.status_code, status.HTTP_200_OK)

        session = AuthSession.objects.get(pk=session_id)
        self.assertEqual(session.status, AuthSession.Status.REVOKED)

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

    def test_login_returns_staff_flag_for_admin_user(self) -> None:
        user = User.objects.create_user(
            email="admin@example.com",
            password="StrongPass123!",
            name="Admin User",
            is_staff=True,
        )

        response = self.client.post(
            reverse("api_v1:authentication:login"),
            {"email": user.email, "password": "StrongPass123!"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertTrue(response.data["data"]["user"]["is_staff"])

    def test_login_rejects_mismatched_account_type(self) -> None:
        user = User.objects.create_user(
            email="team-user@example.com",
            password="StrongPass123!",
            name="Team User",
            account_type=User.AccountType.TEAM,
        )

        response = self.client.post(
            reverse("api_v1:authentication:login"),
            {"email": user.email, "password": "StrongPass123!", "account_type": "personal"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data["success"])

    def test_login_allows_personal_mode_for_team_account_with_personal_workspace_membership(self) -> None:
        user = User.objects.create_user(
            email="hybrid-user@example.com",
            password="StrongPass123!",
            name="Hybrid User",
            account_type=User.AccountType.TEAM,
            primary_mode=User.AccountType.TEAM,
        )
        create_team_with_owner(created_by=user, name="Hybrid Team", is_personal=False)
        create_team_with_owner(created_by=user, name="Hybrid Personal", is_personal=True)

        response = self.client.post(
            reverse("api_v1:authentication:login"),
            {"email": user.email, "password": "StrongPass123!", "account_type": "personal"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data["success"])

    @patch("apps.authentication.services.queue_welcome_email", side_effect=RuntimeError("smtp unavailable"))
    def test_register_succeeds_when_welcome_email_queueing_fails(self, _mock_queue_welcome_email) -> None:
        response = self.client.post(
            reverse("api_v1:authentication:register"),
            {
                "name": "Jane Doe",
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane-welcome@example.com",
                "phone_number": "+254712345678",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "account_type": "personal",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertTrue(User.objects.filter(email="jane-welcome@example.com").exists())

    @patch(
        "apps.authentication.views.send_email_verification",
        side_effect=ServiceUnavailableError("Verification email could not be delivered right now."),
    )
    def test_register_succeeds_when_email_verification_delivery_fails(self, _mock_send_email_verification) -> None:
        response = self.client.post(
            reverse("api_v1:authentication:register"),
            {
                "name": "Jane Verify",
                "email": "jane-verify@example.com",
                "phone_number": "+254712345681",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "account_type": "personal",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["email_verification_delivery"]["status"], "failed")
        self.assertTrue(User.objects.filter(email="jane-verify@example.com").exists())

    @patch("apps.authentication.views.CurrentUserSerializer", side_effect=RuntimeError("serializer unavailable"))
    def test_register_succeeds_when_current_user_serialization_fails(self, _mock_serializer) -> None:
        response = self.client.post(
            reverse("api_v1:authentication:register"),
            {
                "name": "Jane Serializer",
                "email": "jane-serializer@example.com",
                "phone_number": "+254712345679",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "account_type": "personal",
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
                "phone_number": "+254712345680",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "account_type": "personal",
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
            {"email": user.email, "password": "StrongPass123!", "account_type": "personal"},
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
            {"email": user.email, "password": "StrongPass123!", "account_type": "personal"},
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
        token_payload = create_token_pair_for_user(user=user)
        register_auth_session(user=user, token_payload=token_payload, request=self.client.request().wsgi_request)
        self.client.cookies[settings.AUTH_REFRESH_COOKIE_NAME] = token_payload["refresh"]

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
            {"email": user.email, "password": "StrongPass123!", "account_type": "personal"},
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
            {"email": user.email, "password": "StrongPass123!", "account_type": "personal"},
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
            {"email": user.email, "password": "StrongPass123!", "account_type": "personal"},
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

    def test_google_auth_routes_resolve_through_api_namespace(self) -> None:
        self.assertEqual(resolve("/api/v1/auth/google/config/").view_name, "api_v1:authentication:google-config")
        self.assertEqual(resolve("/api/v1/auth/google/login/").view_name, "api_v1:authentication:google-login")
        self.assertEqual(resolve("/api/v1/auth/google/callback/").view_name, "api_v1:authentication:google-callback")

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="client", GOOGLE_OAUTH_CLIENT_SECRET="secret")
    def test_google_login_endpoint_redirects_when_configured(self) -> None:
        response = self.client.get(
            reverse("api_v1:authentication:google-login"),
            {"flow": "login"},
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("accounts.google.com", response["Location"])
        self.assertIn("accounts.google.com", response["Location"])
        self.assertIn("redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fv1%2Fauth%2Fgoogle%2Fcallback%2F", response["Location"])
        self.assertIn("state=", response["Location"])

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="client", GOOGLE_OAUTH_CLIENT_SECRET="secret")
    def test_google_login_endpoint_ignores_invalid_bearer_header(self) -> None:
        self.client.credentials(HTTP_AUTHORIZATION="Bearer stale-or-invalid-token")

        response = self.client.get(
            reverse("api_v1:authentication:google-login"),
            {"flow": "register", "account_type": "team", "team_name": "CUK Team"},
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("accounts.google.com", response["Location"])

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="client", GOOGLE_OAUTH_CLIENT_SECRET="secret")
    def test_google_login_endpoint_requires_account_type_for_register_flow(self) -> None:
        response = self.client.get(reverse("api_v1:authentication:google-login"), {"flow": "register"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("account_type", response.data["errors"])

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
        token_payload = create_token_pair_for_user(user=user)
        authenticate_google_user_mock.return_value = {
            "user": user,
            "tokens": token_payload,
            "is_new_user": False,
        }

        response = self.client.post(
            reverse("api_v1:authentication:google-auth"),
            {"credential": "fake-google-id-token", "account_type": "personal"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["user"]["email"], user.email)
        self.assertEqual(response.data["data"]["user"]["auth_provider"], User.AuthProvider.GOOGLE)
        self.assertEqual(response.data["data"]["user"]["bio"], "Synced from Google")
        self.assertEqual(AuthSession.objects.filter(user=user, status=AuthSession.Status.ACTIVE).count(), 1)
        self.assertIn("refresh_token", response.cookies)
        self.assertTrue(response.data["data"]["tokens"]["refresh_cookie_set"])

    @override_settings(
        GOOGLE_OAUTH_CLIENT_ID="client",
        GOOGLE_OAUTH_CLIENT_SECRET="secret",
        FRONTEND_URL="http://localhost:5173",
    )
    @patch("apps.authentication.adapter.get_google_user_info")
    @patch("apps.authentication.adapter.exchange_code_for_token")
    def test_google_oauth_callback_registers_session_and_uses_cookie_refresh(
        self,
        exchange_code_for_token_mock,
        get_google_user_info_mock,
    ) -> None:
        exchange_code_for_token_mock.return_value = {"access_token": "google-access-token"}
        get_google_user_info_mock.return_value = {
            "email": "callback-user@example.com",
            "given_name": "Callback",
            "family_name": "User",
            "name": "Callback User",
            "picture": "https://example.com/avatar.png",
        }

        response = self.client.get(
            reverse("api_v1:authentication:google-callback"),
            {
                "code": "oauth-code",
                "state": json.dumps(
                    {
                        "next": "/teams/team-99/overview",
                        "account_type": "team",
                        "flow": "register",
                        "team_name": "Callback Team",
                    }
                ),
            },
        )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("/auth/google/callback?", response["Location"])
        self.assertIn("next=%2Fteams%2Fteam-99%2Foverview", response["Location"])
        self.assertNotIn("refresh=", response["Location"])
        self.assertIn("refresh_token", response.cookies)

        user = User.objects.get(email="callback-user@example.com")
        self.assertEqual(user.auth_provider, User.AuthProvider.GOOGLE)
        self.assertEqual(user.account_type, User.AccountType.TEAM)
        self.assertTrue(AuthSession.objects.filter(user=user, status=AuthSession.Status.ACTIVE).exists())
