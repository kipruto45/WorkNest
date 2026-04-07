from __future__ import annotations

from datetime import timedelta
from unittest.mock import Mock, patch

from django.test import TestCase
from django.utils import timezone

from apps.comments.services import create_comment
from apps.memberships.models import TeamInvitation
from apps.notifications.constants import NotificationType
from apps.notifications.models import Notification
from apps.notifications.services import create_notification, notify_team_invite
from apps.realtime.constants import (
    COMMENT_CREATED_EVENT,
    NOTIFICATION_CREATED_EVENT,
    NOTIFICATION_UNREAD_COUNT_EVENT,
    TASK_ASSIGNED_EVENT,
    TEAM_INVITE_RECEIVED_EVENT,
)
from apps.realtime.services import send_team_event, send_unread_count_event, send_user_event
from apps.realtime.tests.utils import RealtimeFixtureMixin
from apps.tasks.services import assign_task


class RealtimeServiceTests(RealtimeFixtureMixin, TestCase):
    def test_send_user_event_dispatches_to_personal_group(self) -> None:
        channel_layer = Mock()

        with patch("apps.realtime.services.get_channel_layer", return_value=channel_layer), patch(
            "apps.realtime.services.async_to_sync", side_effect=lambda func: func
        ):
            send_user_event(user_id=self.member.id, event_name=NOTIFICATION_CREATED_EVENT, payload={"id": "1"})

        channel_layer.group_send.assert_called_once_with(
            f"user_{self.member.id}",
            {
                "type": NOTIFICATION_CREATED_EVENT,
                "event": NOTIFICATION_CREATED_EVENT,
                "data": {"id": "1"},
            },
        )

    def test_send_team_event_dispatches_to_team_group(self) -> None:
        channel_layer = Mock()

        with patch("apps.realtime.services.get_channel_layer", return_value=channel_layer), patch(
            "apps.realtime.services.async_to_sync", side_effect=lambda func: func
        ):
            send_team_event(team_id=self.team.id, event_name="comment.created", payload={"comment_id": "1"})

        channel_layer.group_send.assert_called_once()
        args, _kwargs = channel_layer.group_send.call_args
        self.assertEqual(args[0], f"team_{self.team.id}")
        self.assertEqual(args[1]["event"], COMMENT_CREATED_EVENT)

    def test_send_unread_count_event_formats_payload(self) -> None:
        Notification.objects.create(
            user=self.member,
            type=NotificationType.TASK_ASSIGNED,
            title="Unread",
            message="Unread notification",
            team=self.team,
        )
        captured: dict = {}

        def _capture(*, user_id, event_name, payload):
            captured["user_id"] = user_id
            captured["event_name"] = event_name
            captured["payload"] = payload

        with patch("apps.realtime.services.send_user_event", side_effect=_capture):
            send_unread_count_event(user=self.member)

        self.assertEqual(captured["user_id"], self.member.id)
        self.assertEqual(captured["event_name"], NOTIFICATION_UNREAD_COUNT_EVENT)
        self.assertEqual(captured["payload"], {"unread_count": 1})

    def test_notification_creation_triggers_realtime_pushes_on_commit(self) -> None:
        with patch("apps.notifications.services.send_notification_event") as send_notification_event_mock, patch(
            "apps.notifications.services.send_unread_count_event"
        ) as send_unread_count_event_mock, patch("apps.notifications.services.queue_email_notification"):
            with self.captureOnCommitCallbacks(execute=True):
                create_notification(
                    user=self.member,
                    notification_type=NotificationType.TASK_ASSIGNED,
                    title="Assigned",
                    message="Task assigned",
                    actor=self.owner,
                    team=self.team,
                )

        send_notification_event_mock.assert_called_once()
        send_unread_count_event_mock.assert_called_once_with(user=self.member)

    def test_task_assignment_triggers_realtime_assignment_event(self) -> None:
        with patch("apps.tasks.services.send_task_assignment_event") as send_task_assignment_event_mock, patch(
            "apps.notifications.services.notify_task_assignment"
        ):
            with self.captureOnCommitCallbacks(execute=True):
                assign_task(task=self.task, user=self.manager, actor=self.owner)

        send_task_assignment_event_mock.assert_called_once_with(task=self.task, actor=self.owner)

    def test_comment_creation_triggers_team_comment_event(self) -> None:
        with patch("apps.comments.services.send_comment_event") as send_comment_event_mock, patch(
            "apps.notifications.services.notify_comment_activity"
        ):
            with self.captureOnCommitCallbacks(execute=True):
                create_comment(task=self.task, author=self.owner, content="Please review this")

        send_comment_event_mock.assert_called_once()
        self.assertEqual(send_comment_event_mock.call_args.kwargs["event_name"], COMMENT_CREATED_EVENT)

    def test_team_invite_notification_triggers_explicit_invite_event(self) -> None:
        invitation = TeamInvitation.objects.create(
            team=self.team,
            email=self.member.email,
            role="member",
            token="token-123",
            invited_by=self.owner,
            expires_at=timezone.now() + timedelta(days=7),
        )

        with patch("apps.notifications.services.send_team_invite_event") as send_team_invite_event_mock, patch(
            "apps.notifications.services.send_notification_event"
        ), patch("apps.notifications.services.send_unread_count_event"):
            with self.captureOnCommitCallbacks(execute=True):
                notify_team_invite(invitation=invitation, recipient_user=self.member)

        send_team_invite_event_mock.assert_called_once_with(invitation=invitation, recipient_user=self.member)
