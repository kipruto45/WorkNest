from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.notifications.constants import NotificationType
from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationDetailSerializer, NotificationListQuerySerializer

User = get_user_model()


class NotificationSerializerTests(TestCase):
    def test_notification_detail_serializer_includes_actor_and_metadata(self) -> None:
        actor = User.objects.create_user(email="actor@example.com", password="StrongPass123!", name="Actor")
        user = User.objects.create_user(email="user@example.com", password="StrongPass123!", name="User")
        notification = Notification.objects.create(
            user=user,
            actor=actor,
            type=NotificationType.MENTIONED_IN_COMMENT,
            title="Mentioned",
            message="You were mentioned in a comment.",
            metadata={"comment_id": "456"},
        )

        data = NotificationDetailSerializer(notification).data

        self.assertEqual(data["actor"]["email"], actor.email)
        self.assertEqual(data["metadata"]["comment_id"], "456")

    def test_list_query_serializer_rejects_invalid_type(self) -> None:
        serializer = NotificationListQuerySerializer(data={"type": "invalid"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("type", serializer.errors)
