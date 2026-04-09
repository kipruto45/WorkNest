import shutil
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.models import CredentialChangeRequest

User = get_user_model()


class UserProfileEndpointTests(APITestCase):
    def setUp(self) -> None:
        self._temp_media_root = tempfile.mkdtemp(prefix="user-profile-media-")
        self.user = User.objects.create_user(
            email="jane@example.com",
            password="StrongPass123!",
            name="Jane Doe",
        )
        access = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def tearDown(self) -> None:
        shutil.rmtree(self._temp_media_root, ignore_errors=True)

    def test_get_profile_returns_authenticated_user(self) -> None:
        response = self.client.get(reverse("api_v1:users:me"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["email"], self.user.email)

    def test_patch_profile_updates_supported_fields(self) -> None:
        response = self.client.patch(
            reverse("api_v1:users:me"),
            {"name": "Jane Updated", "first_name": "Jane", "last_name": "Updated", "bio": "Backend builder"},
            format="json",
        )

        self.user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user.name, "Jane Updated")
        self.assertEqual(self.user.first_name, "Jane")
        self.assertEqual(self.user.last_name, "Updated")
        self.assertEqual(self.user.bio, "Backend builder")

    @override_settings(MEDIA_ROOT="/tmp")
    def test_patch_profile_accepts_avatar_upload(self) -> None:
        uploaded = SimpleUploadedFile("avatar.png", b"fake-image-bytes", content_type="image/png")

        with override_settings(MEDIA_ROOT=self._temp_media_root, MEDIA_URL="/media/"):
            response = self.client.patch(
                reverse("api_v1:users:me"),
                {"name": "Jane Doe", "avatar_file": uploaded},
                format="multipart",
            )

        self.user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("/media/avatars/", self.user.avatar)

    def test_admin_search_returns_matching_non_staff_users(self) -> None:
        User.objects.create_user(
            email="learner@example.com",
            password="StrongPass123!",
            name="Learner One",
        )
        User.objects.create_user(
            email="staff@example.com",
            password="StrongPass123!",
            name="Staff Member",
            is_staff=True,
        )
        admin_user = User.objects.create_user(
            email="admin@example.com",
            password="StrongPass123!",
            name="Admin",
            is_staff=True,
        )
        access = str(RefreshToken.for_user(admin_user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = self.client.get(reverse("api_v1:users:admin-search"), {"q": "learner"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(response.data["data"]["results"][0]["email"], "learner@example.com")

    @override_settings(ADMIN_EMAIL="kiprutovictor39@gmail.com")
    def test_admin_search_rejects_staff_user_when_not_configured_admin(self) -> None:
        non_admin_staff = User.objects.create_user(
            email="other-staff@example.com",
            password="StrongPass123!",
            name="Other Staff",
            is_staff=True,
        )
        access = str(RefreshToken.for_user(non_admin_staff).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = self.client.get(reverse("api_v1:users:admin-search"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patch_notification_preferences_persists_channel_matrix_and_sms_rules(self) -> None:
        response = self.client.patch(
            reverse("api_v1:users:me-notification-preferences"),
            {
                "channels": {
                    "in_app": {"task_assigned": False},
                    "email": {"mentioned_in_comment": False, "team_invite": False},
                },
                "task_assignment_sms": False,
                "invite_sms": False,
            },
            format="json",
        )

        self.user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.user.notification_preferences["channels"]["in_app"]["task_assigned"])
        self.assertFalse(self.user.notification_preferences["channels"]["email"]["mentioned_in_comment"])
        self.assertFalse(self.user.notification_preferences["channels"]["email"]["team_invite"])
        self.assertFalse(self.user.sms_preferences["task_assignment_sms"])
        self.assertFalse(self.user.sms_preferences["invite_sms"])

    @patch("apps.authentication.services.queue_credential_change_email")
    def test_request_email_change_sends_code_before_updating_profile(self, mocked_queue_email) -> None:
        response = self.client.post(
            reverse("api_v1:users:me-credential-change-request"),
            {
                "credential_type": "email",
                "new_value": "new-email@example.com",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        change_request = CredentialChangeRequest.objects.get(user=self.user, credential_type="email")
        self.assertEqual(change_request.new_value, "new-email@example.com")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "jane@example.com")
        mocked_queue_email.assert_called_once()

    @patch("apps.authentication.services.queue_credential_change_email")
    def test_confirm_email_change_updates_profile_and_login_identity(self, mocked_queue_email) -> None:
        request_response = self.client.post(
            reverse("api_v1:users:me-credential-change-request"),
            {
                "credential_type": "email",
                "new_value": "new-email@example.com",
            },
            format="json",
        )
        self.assertEqual(request_response.status_code, status.HTTP_200_OK, request_response.data)
        change_request = CredentialChangeRequest.objects.get(user=self.user, credential_type="email")

        response = self.client.post(
            reverse("api_v1:users:me-credential-change-confirm"),
            {
                "credential_type": "email",
                "code": change_request.code,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "new-email@example.com")
        self.assertTrue(self.user.email_verified)
        mocked_queue_email.assert_called_once()

    @patch("apps.authentication.services.queue_sms")
    def test_confirm_phone_change_updates_profile_after_code_verification(self, mocked_queue_sms) -> None:
        self.user.phone_number = "+254711000001"
        self.user.phone_country_code = "+254"
        self.user.phone_verified = True
        self.user.save(update_fields=["phone_number", "phone_country_code", "phone_verified", "updated_at"])

        request_response = self.client.post(
            reverse("api_v1:users:me-credential-change-request"),
            {
                "credential_type": "phone",
                "new_value": "+254711000099",
                "phone_country_code": "+254",
            },
            format="json",
        )
        self.assertEqual(request_response.status_code, status.HTTP_200_OK, request_response.data)
        change_request = CredentialChangeRequest.objects.get(user=self.user, credential_type="phone")

        response = self.client.post(
            reverse("api_v1:users:me-credential-change-confirm"),
            {
                "credential_type": "phone",
                "code": change_request.code,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, "+254711000099")
        self.assertTrue(self.user.phone_verified)
        mocked_queue_sms.assert_called_once()

    def test_phone_settings_reject_direct_phone_replacement(self) -> None:
        self.user.phone_number = "+254711000001"
        self.user.phone_country_code = "+254"
        self.user.save(update_fields=["phone_number", "phone_country_code", "updated_at"])

        response = self.client.patch(
            reverse("api_v1:users:me-phone"),
            {
                "phone_number": "+254711000099",
                "phone_country_code": "+254",
                "sms_opt_in": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data["errors"])
