import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

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
