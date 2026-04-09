from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserViewTests(APITestCase):
    def test_users_me_requires_authentication(self) -> None:
        response = self.client.get(reverse("api_v1:users:me"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_users_me_patch_rejects_invalid_timezone(self) -> None:
        user = User.objects.create_user(
            email="jane@example.com",
            password="StrongPass123!",
            name="Jane Doe",
        )
        access = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = self.client.patch(
            reverse("api_v1:users:me"),
            {"timezone": "Mars/Phobos"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_users_me_patch_updates_notification_preferences(self) -> None:
        user = User.objects.create_user(
            email="jane@example.com",
            password="StrongPass123!",
            name="Jane Doe",
        )
        access = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        response = self.client.patch(
            reverse("api_v1:users:me"),
            {
                "notification_preferences": {
                    "channels": {"in_app": {"task_assigned": True}, "email": {"task_assigned": False}},
                    "mention_emails": False,
                }
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertIn("channels", user.notification_preferences)
        self.assertFalse(user.notification_preferences.get("channels", {}).get("email", {}).get("task_assigned"))
