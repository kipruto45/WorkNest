from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.notifications.constants import NotificationType
from apps.notifications.models import Notification

User = get_user_model()


class NotificationModelTests(TestCase):
    def test_notification_defaults_and_metadata(self) -> None:
        user = User.objects.create_user(email="user@example.com", password="StrongPass123!", name="User")
        notification = Notification.objects.create(
            user=user,
            type=NotificationType.TASK_ASSIGNED,
            title="Assigned",
            message="A task was assigned to you.",
            metadata={"task_id": "123"},
        )

        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)
        self.assertEqual(notification.metadata["task_id"], "123")
