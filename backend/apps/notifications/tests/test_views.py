from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.notifications.constants import NotificationType
from apps.notifications.models import Notification

User = get_user_model()


class NotificationViewTests(APITestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(email="user@example.com", password="StrongPass123!", name="User")
        self.other_user = User.objects.create_user(email="other@example.com", password="StrongPass123!", name="Other")
        self.notification = Notification.objects.create(
            user=self.user,
            type=NotificationType.TASK_ASSIGNED,
            title="Assigned",
            message="A task was assigned to you.",
        )
        self.other_notification = Notification.objects.create(
            user=self.other_user,
            type=NotificationType.COMMENT_POSTED,
            title="Comment",
            message="A comment was posted.",
        )

    def authenticate(self, user) -> None:
        access = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_list_returns_only_own_notifications(self) -> None:
        self.authenticate(self.user)

        response = self.client.get(reverse("api_v1:notifications:list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(response.data["data"]["results"][0]["id"], str(self.notification.id))

    def test_detail_rejects_other_users_notification(self) -> None:
        self.authenticate(self.user)

        response = self.client.get(reverse("api_v1:notifications:detail", args=[self.other_notification.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unread_count_endpoint_returns_count(self) -> None:
        self.authenticate(self.user)

        response = self.client.get(reverse("api_v1:notifications:unread-count"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["unread_count"], 1)

    def test_mark_read_and_unread_work(self) -> None:
        self.authenticate(self.user)

        read_response = self.client.patch(reverse("api_v1:notifications:mark-read", args=[self.notification.id]))
        unread_response = self.client.patch(reverse("api_v1:notifications:mark-unread", args=[self.notification.id]))

        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        self.assertEqual(unread_response.status_code, status.HTTP_200_OK)
        self.notification.refresh_from_db()
        self.assertFalse(self.notification.is_read)

    def test_mark_all_read_marks_only_current_users_notifications(self) -> None:
        self.authenticate(self.user)

        response = self.client.patch(reverse("api_v1:notifications:mark-all-read"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.notification.refresh_from_db()
        self.other_notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
        self.assertFalse(self.other_notification.is_read)

    def test_delete_notification_removes_owned_notification(self) -> None:
        self.authenticate(self.user)

        response = self.client.delete(reverse("api_v1:notifications:detail", args=[self.notification.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Notification.objects.filter(id=self.notification.id).exists())

    def test_unauthenticated_access_is_rejected(self) -> None:
        response = self.client.get(reverse("api_v1:notifications:list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_admin_can_send_notification_to_selected_users(self) -> None:
        admin_user = User.objects.create_user(
            email="admin@example.com",
            password="StrongPass123!",
            name="Admin",
            is_staff=True,
        )
        self.authenticate(admin_user)

        response = self.client.post(
            reverse("api_v1:notifications:admin-send"),
            {
                "scope": "selected",
                "title": "Heads up",
                "message": "Please check the updated lab schedule.",
                "user_ids": [str(self.user.id)],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["count"], 1)
        created = Notification.objects.filter(user=self.user, type=NotificationType.ADMIN_MESSAGE).latest("created_at")
        self.assertEqual(created.title, "Heads up")
        self.assertEqual(created.actor_id, admin_user.id)

    def test_non_admin_cannot_send_admin_notification(self) -> None:
        self.authenticate(self.user)

        response = self.client.post(
            reverse("api_v1:notifications:admin-send"),
            {
                "scope": "all",
                "message": "This should not be allowed.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
