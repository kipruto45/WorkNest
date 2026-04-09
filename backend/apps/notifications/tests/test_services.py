from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from unittest.mock import patch

from apps.comments.models import Comment
from apps.integrations.models import EmailDelivery, SMSDelivery
from apps.notifications.constants import NotificationType
from apps.notifications.models import Notification
from apps.notifications.services import (
    create_admin_communication,
    create_bulk_notifications,
    create_notification,
    notify_comment_activity,
    notify_task_assignment,
    notify_team_invite,
    should_send_email_for_type,
)
from apps.tasks.models import Task
from apps.teams.services import create_team_with_owner
from apps.memberships.models import TeamInvitation, Membership

User = get_user_model()


@override_settings(SMS_ENABLED=True, CELERY_TASK_ALWAYS_EAGER=True)
class NotificationServiceTests(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        self.member = User.objects.create_user(
            email="member@example.com",
            password="StrongPass123!",
            name="Member",
            phone_number="+254711000001",
            phone_verified=True,
            sms_opt_in=True,
        )
        self.assignee = User.objects.create_user(
            email="assignee@example.com",
            password="StrongPass123!",
            name="Assignee",
            phone_number="+254711000002",
            phone_verified=True,
            sms_opt_in=True,
        )
        self.team = create_team_with_owner(created_by=self.owner, name="Platform")
        self.team.memberships.create(
            user=self.member,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
        )
        self.team.memberships.create(
            user=self.assignee,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
        )

    def test_create_notification_persists_record(self) -> None:
        notification = create_notification(
            user=self.member,
            notification_type=NotificationType.COMMENT_POSTED,
            title="Comment",
            message="A teammate commented.",
            actor=self.owner,
            metadata={"task_id": "1"},
        )

        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(notification.user, self.member)

    def test_create_bulk_notifications_creates_multiple_records(self) -> None:
        notifications = create_bulk_notifications(
            users=[self.member, self.assignee],
            notification_type=NotificationType.COMMENT_POSTED,
            title="Task updated",
            message_builder=lambda user: f"Hello {user.name}",
            actor=self.owner,
        )

        self.assertEqual(len(notifications), 2)
        self.assertEqual(Notification.objects.count(), 2)

    def test_notify_task_assignment_creates_notification(self) -> None:
        task = Task.objects.create(
            team=self.team,
            title="Build API",
            created_by=self.owner,
            assigned_to=self.assignee,
            due_date=timezone.now() + timedelta(days=1),
        )

        with patch(
            "apps.integrations.sms.services.deliver_sms_message",
            return_value={"provider": "africas_talking", "message_id": "msg-task", "status": "sent"},
        ), self.captureOnCommitCallbacks(execute=True):
            notification = notify_task_assignment(task=task, actor=self.owner)

        self.assertIsNotNone(notification)
        self.assertEqual(notification.type, NotificationType.TASK_ASSIGNED)
        self.assertEqual(notification.user, self.assignee)
        self.assertEqual(SMSDelivery.objects.filter(message_type=NotificationType.TASK_ASSIGNED).count(), 1)

    def test_notify_team_invite_creates_in_app_notification(self) -> None:
        invitation = TeamInvitation.objects.create(
            team=self.team,
            email=self.member.email,
            role=Membership.Role.MEMBER,
            invited_by=self.owner,
            expires_at=timezone.now() + timedelta(days=1),
        )

        with patch(
            "apps.integrations.sms.services.deliver_sms_message",
            return_value={"provider": "africas_talking", "message_id": "msg-invite", "status": "sent"},
        ), patch("apps.notifications.services.send_team_invite_event"), self.captureOnCommitCallbacks(execute=True):
            notification = notify_team_invite(invitation=invitation, recipient_user=self.member)

        self.assertIsNotNone(notification)
        self.assertEqual(notification.type, NotificationType.TEAM_INVITE)
        self.assertEqual(notification.metadata["invitation_token"], invitation.token)
        self.assertEqual(SMSDelivery.objects.filter(message_type=NotificationType.TEAM_INVITE).count(), 1)

    def test_notify_comment_activity_creates_mention_and_comment_notifications(self) -> None:
        task = Task.objects.create(
            team=self.team,
            title="Review API",
            created_by=self.owner,
            assigned_to=self.assignee,
        )
        comment = Comment.objects.create(
            task=task,
            author=self.owner,
            content="Please review this @member",
        )

        with patch(
            "apps.integrations.sms.services.deliver_sms_message",
            return_value={"provider": "africas_talking", "message_id": "msg-mention", "status": "sent"},
        ), self.captureOnCommitCallbacks(execute=True):
            notifications = notify_comment_activity(comment=comment, mentions=[self.member])

        self.assertEqual(Notification.objects.count(), 2)
        mention_types = {notification.type for notification in notifications}
        self.assertIn(NotificationType.MENTIONED_IN_COMMENT, mention_types)
        self.assertIn(NotificationType.COMMENT_POSTED, mention_types)
        self.assertEqual(SMSDelivery.objects.filter(message_type=NotificationType.MENTIONED_IN_COMMENT).count(), 1)

    def test_notify_comment_activity_sends_one_email_per_recipient(self) -> None:
        task = Task.objects.create(
            team=self.team,
            title="Review API",
            created_by=self.owner,
            assigned_to=self.assignee,
        )
        comment = Comment.objects.create(
            task=task,
            author=self.owner,
            content="Please review this @member",
        )

        with patch(
            "apps.integrations.sms.services.deliver_sms_message",
            return_value={"provider": "africas_talking", "message_id": "msg-email-test", "status": "sent"},
        ), self.captureOnCommitCallbacks(execute=True):
            notify_comment_activity(comment=comment, mentions=[self.member])

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(EmailDelivery.objects.filter(email_type="mentioned_in_comment").count(), 1)
        self.assertEqual(EmailDelivery.objects.filter(email_type="comment_posted").count(), 1)

    def test_comment_posted_notifications_are_email_eligible(self) -> None:
        self.assertTrue(should_send_email_for_type(notification_type=NotificationType.COMMENT_POSTED))

    def test_admin_communication_supports_sms_broadcasts(self) -> None:
        with patch(
            "apps.integrations.sms.services.deliver_sms_message",
            return_value={"provider": "africas_talking", "message_id": "msg-admin", "status": "sent"},
        ):
            result = create_admin_communication(
                actor=self.owner,
                audience_type="selected_users",
                channel_type="sms",
                title="Urgent update",
                message="Deployment starts at 21:00.",
                user_ids=[str(self.member.id)],
                confirm_broadcast=True,
            )

        communication = result["communication"]
        communication.refresh_from_db()
        self.assertEqual(communication.delivered_sms_count, 1)
        self.assertEqual(communication.failed_sms_count, 0)
