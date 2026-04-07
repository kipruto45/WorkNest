from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.integrations.models import EmailDelivery
from apps.notifications.constants import NotificationType
from apps.notifications.models import Notification
from apps.notifications.tasks import send_deadline_approaching_notifications_task, send_notification_email_task
from apps.tasks.models import Task
from apps.teams.services import create_team_with_owner
from apps.memberships.models import Membership

User = get_user_model()


class NotificationTaskTests(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        self.assignee = User.objects.create_user(email="assignee@example.com", password="StrongPass123!", name="Assignee")
        self.team = create_team_with_owner(created_by=self.owner, name="Platform")
        self.team.memberships.create(
            user=self.assignee,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
        )

    def test_send_notification_email_task_sends_email(self) -> None:
        notification = Notification.objects.create(
            user=self.assignee,
            actor=self.owner,
            type=NotificationType.TASK_ASSIGNED,
            title="Task assigned to you",
            message="A task was assigned to you.",
        )

        result = send_notification_email_task(str(notification.id))

        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(notification.title, mail.outbox[0].subject)

    @override_settings(NOTIFICATION_DEADLINE_REMINDER_WINDOWS_HOURS=[24], NOTIFICATION_DEADLINE_REMINDER_GRACE_MINUTES=60)
    def test_deadline_notification_task_creates_reminder(self) -> None:
        Task.objects.create(
            team=self.team,
            title="Due soon",
            created_by=self.owner,
            assigned_to=self.assignee,
            due_date=timezone.now() + timedelta(hours=24),
        )

        created_count = send_deadline_approaching_notifications_task()

        self.assertEqual(created_count, 1)
        self.assertTrue(
            Notification.objects.filter(
                user=self.assignee,
                type=NotificationType.DEADLINE_APPROACHING,
            ).exists()
        )
        self.assertTrue(EmailDelivery.objects.filter(email_type="deadline_approaching", recipient_email=self.assignee.email).exists())
