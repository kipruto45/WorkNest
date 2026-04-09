from __future__ import annotations

import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.comments.models import Comment
from apps.integrations.email.base import EmailMessagePayload
from apps.integrations.email.builders import (
    build_attachment_uploaded_email_payload,
    build_comment_posted_email_payload,
    build_deadline_approaching_email_payload,
    build_invitation_accepted_email_payload,
    build_invitation_reminder_email_payload,
    build_invitation_revoked_email_payload,
    build_mentioned_email_payload,
    build_password_reset_email_payload,
    build_role_changed_email_payload,
    build_task_assigned_email_payload,
    build_task_status_changed_email_payload,
    build_team_invite_email_payload,
    build_welcome_email_payload,
)
from apps.integrations.email.sendgrid import SendGridEmailProvider
from apps.integrations.email.services import (
    get_email_provider,
    queue_notification_email,
    queue_password_reset_email,
    queue_team_invite_email,
    queue_welcome_email,
    send_system_email,
)
from apps.integrations.exceptions import EmailSendFailedError
from apps.integrations.models import EmailDelivery
from apps.memberships.models import Membership, TeamInvitation
from apps.notifications.constants import NotificationType
from apps.notifications.models import Notification
from apps.attachments.models import Attachment
from apps.tasks.models import Task
from apps.teams.services import create_team_with_owner

User = get_user_model()


class DummySendGridResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class EmailWorkflowTests(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        self.member = User.objects.create_user(email="member@example.com", password="StrongPass123!", name="Member")
        self.team = create_team_with_owner(created_by=self.owner, name="Platform")
        self.team.memberships.create(
            user=self.member,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
        )

    def test_provider_selection_defaults_to_smtp(self) -> None:
        provider = get_email_provider()
        self.assertEqual(provider.provider_name, "smtp")

    def test_smtp_system_email_sends_through_django_backend(self) -> None:
        result = send_system_email(
            payload=EmailMessagePayload(
                to=["user@example.com"],
                subject="Hello",
                text_body="Plain text body",
            )
        )

        self.assertEqual(result["provider"], "smtp")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Hello")

    @override_settings(PASSWORD_RESET_LINK_BASE_URL="http://localhost:5173/reset-password")
    def test_password_reset_email_is_queued_delivered_and_tracked(self) -> None:
        user = User.objects.create_user(email="user@example.com", password="StrongPass123!", name="User")

        delivery = queue_password_reset_email(
            user=user,
            reset_url="http://localhost:5173/reset-password?uid=test&token=abc",
            actor=user,
        )
        delivery.refresh_from_db()

        self.assertEqual(delivery.status, EmailDelivery.Status.SENT)
        self.assertEqual(delivery.email_type, "password_reset")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Reset your password", mail.outbox[0].subject)
        self.assertNotIn("<html", mail.outbox[0].body.lower())
        self.assertIn("reset-password?uid=test&token=abc", mail.outbox[0].body)
        self.assertEqual(len(mail.outbox[0].alternatives), 1)

    def test_team_invitation_email_is_queued_and_uses_modern_template(self) -> None:
        invitation = TeamInvitation.objects.create(
            team=self.team,
            email="invitee@example.com",
            role=Membership.Role.MANAGER,
            invited_by=self.owner,
            expires_at=timezone.now() + timedelta(days=7),
            custom_message="We'd like you to help coordinate delivery on this workspace.",
        )

        delivery = queue_team_invite_email(invitation=invitation, actor=self.owner)
        delivery.refresh_from_db()

        self.assertEqual(delivery.status, EmailDelivery.Status.SENT)
        self.assertEqual(delivery.related_object_type, "team_invitation")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Platform", mail.outbox[0].subject)
        self.assertIn("Accept Invitation", mail.outbox[0].alternatives[0][0])
        self.assertIn("coordinate delivery", mail.outbox[0].body)

    def test_notification_email_uses_task_and_comment_metadata(self) -> None:
        task = Task.objects.create(
            team=self.team,
            title="Review analytics",
            description="Check the dashboard cards and polish the charts.",
            created_by=self.owner,
            assigned_to=self.member,
            priority=Task.Priority.HIGH,
        )
        comment = Comment.objects.create(
            task=task,
            author=self.owner,
            content="Please review the chart labels before launch.",
        )
        notification = Notification.objects.create(
            user=self.member,
            actor=self.owner,
            team=self.team,
            type=NotificationType.COMMENT_POSTED,
            title="New comment on a task",
            message="Owner commented on Review analytics.",
            metadata={
                "task_id": str(task.id),
                "comment_id": str(comment.id),
                "team_id": str(self.team.id),
            },
            target_type="comment",
            target_id=comment.id,
        )

        delivery = queue_notification_email(notification=notification)
        delivery.refresh_from_db()

        self.assertEqual(delivery.status, EmailDelivery.Status.SENT)
        self.assertEqual(delivery.email_type, "comment_posted")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Review analytics", mail.outbox[0].subject)
        self.assertIn("Please review the chart labels", mail.outbox[0].body)
        self.assertIn("Open Discussion", mail.outbox[0].alternatives[0][0])

    @override_settings(FRONTEND_URL="http://localhost:5173")
    def test_all_transactional_email_buttons_use_real_frontend_routes(self) -> None:
        invitation = TeamInvitation.objects.create(
            team=self.team,
            email="invitee@example.com",
            role=Membership.Role.MANAGER,
            invited_by=self.owner,
            expires_at=timezone.now() + timedelta(days=7),
        )
        task = Task.objects.create(
            team=self.team,
            title="Launch checklist",
            description="Review launch blockers and confirm readiness.",
            created_by=self.owner,
            assigned_to=self.member,
            priority=Task.Priority.HIGH,
            due_date=timezone.now() + timedelta(days=2),
        )
        comment = Comment.objects.create(
            task=task,
            author=self.owner,
            content="Please review the final details before tomorrow.",
        )
        attachment = Attachment.objects.create(
            task=task,
            uploaded_by=self.owner,
            original_name="launch-plan.pdf",
            file_name="launch-plan.pdf",
            file_path="attachments/launch-plan.pdf",
            file_url="http://localhost:8000/files/attachments/launch-plan.pdf",
            file_size=2048,
            mime_type="application/pdf",
        )
        membership = Membership.objects.get(team=self.team, user=self.member)
        task.status = Task.Status.DONE
        task.save(update_fields=["status", "updated_at"])

        payloads = [
            build_password_reset_email_payload(
                user=self.member,
                reset_url="http://localhost:5173/reset-password?uid=test&token=abc",
            ),
            build_team_invite_email_payload(invitation=invitation),
            build_invitation_reminder_email_payload(invitation=invitation),
            build_invitation_revoked_email_payload(invitation=invitation, actor=self.owner),
            build_task_assigned_email_payload(task=task, assigner=self.owner, assignee=self.member),
            build_deadline_approaching_email_payload(task=task, recipient=self.member, reminder_window_hours=24),
            build_comment_posted_email_payload(comment=comment, task=task, recipient=self.member),
            build_mentioned_email_payload(comment=comment, task=task, mentioned_user=self.member),
            build_welcome_email_payload(user=self.member),
            build_invitation_accepted_email_payload(invitation=invitation, recipient_user=self.owner, actor=self.member),
            build_role_changed_email_payload(
                membership=membership,
                actor=self.owner,
                old_role=Membership.Role.MEMBER,
                new_role=Membership.Role.MANAGER,
            ),
            build_task_status_changed_email_payload(
                task=task,
                previous_status=Task.Status.IN_PROGRESS,
                changed_by=self.owner,
                recipient=self.member,
            ),
            build_attachment_uploaded_email_payload(attachment=attachment, recipient=self.member),
        ]

        for payload in payloads:
            with self.subTest(email_type=payload.email_type):
                self.assertTrue(payload.context["button_url"])
                self.assertTrue(payload.context["button_url"].startswith("http://localhost:5173/"))
                self.assertNotIn("None", payload.context["button_url"])
                self.assertNotIn("//tasks", payload.context["button_url"])
                if payload.email_type == "welcome":
                    self.assertEqual(payload.context["button_url"], "http://localhost:5173/dashboard")
                if payload.email_type == "team_invite":
                    self.assertEqual(payload.context["decline_url"], payload.context["button_url"])
                if payload.email_type == "invitation_revoked":
                    self.assertIn("/invitations/", payload.context["button_url"])

    @override_settings(
        FRONTEND_URL="http://localhost:5173",
        PUBLIC_WEBAPP_URL="https://worknested.netlify.app",
        PASSWORD_RESET_LINK_BASE_URL="https://worknested.netlify.app/reset-password",
        LOGO_URL="https://worknested.netlify.app/logo_hd.png",
    )
    def test_transactional_email_buttons_prefer_public_webapp_urls(self) -> None:
        invitation = TeamInvitation.objects.create(
            team=self.team,
            email="invitee@example.com",
            role=Membership.Role.MANAGER,
            invited_by=self.owner,
            expires_at=timezone.now() + timedelta(days=7),
        )
        task = Task.objects.create(
            team=self.team,
            title="Public route check",
            description="Ensure hosted links are used in email payloads.",
            created_by=self.owner,
            assigned_to=self.member,
            priority=Task.Priority.HIGH,
            due_date=timezone.now() + timedelta(days=2),
        )
        comment = Comment.objects.create(
            task=task,
            author=self.owner,
            content="Hosted links should point to the deployed app.",
        )
        attachment = Attachment.objects.create(
            task=task,
            uploaded_by=self.owner,
            original_name="public-routes.pdf",
            file_name="public-routes.pdf",
            file_path="attachments/public-routes.pdf",
            file_url="https://worknest-backend-t6dw.onrender.com/files/attachments/public-routes.pdf",
            file_size=2048,
            mime_type="application/pdf",
        )
        membership = Membership.objects.get(team=self.team, user=self.member)

        payloads = [
            build_password_reset_email_payload(
                user=self.member,
                reset_url="https://worknested.netlify.app/reset-password?uid=test&token=abc",
            ),
            build_team_invite_email_payload(invitation=invitation),
            build_invitation_reminder_email_payload(invitation=invitation),
            build_invitation_revoked_email_payload(invitation=invitation, actor=self.owner),
            build_task_assigned_email_payload(task=task, assigner=self.owner, assignee=self.member),
            build_deadline_approaching_email_payload(task=task, recipient=self.member, reminder_window_hours=24),
            build_comment_posted_email_payload(comment=comment, task=task, recipient=self.member),
            build_mentioned_email_payload(comment=comment, task=task, mentioned_user=self.member),
            build_welcome_email_payload(user=self.member),
            build_invitation_accepted_email_payload(invitation=invitation, recipient_user=self.owner, actor=self.member),
            build_role_changed_email_payload(
                membership=membership,
                actor=self.owner,
                old_role=Membership.Role.MEMBER,
                new_role=Membership.Role.MANAGER,
            ),
            build_task_status_changed_email_payload(
                task=task,
                previous_status=Task.Status.IN_PROGRESS,
                changed_by=self.owner,
                recipient=self.member,
            ),
            build_attachment_uploaded_email_payload(attachment=attachment, recipient=self.member),
        ]

        for payload in payloads:
            with self.subTest(email_type=payload.email_type):
                self.assertIn("https://worknested.netlify.app", payload.context["button_url"])
                self.assertNotIn("http://localhost:5173", payload.context["button_url"])

        self.assertEqual(
            build_team_invite_email_payload(invitation=invitation).context["button_url"],
            f"https://worknested.netlify.app/invitations/{invitation.token}",
        )
        self.assertEqual(
            build_welcome_email_payload(user=self.member).context["button_url"],
            "https://worknested.netlify.app/dashboard",
        )

    @override_settings(
        ENVIRONMENT="production",
        FRONTEND_URL="http://localhost:5173",
        PUBLIC_WEBAPP_URL="",
        PASSWORD_RESET_LINK_BASE_URL="",
        INVITE_LINK_BASE_URL="",
        LOGO_URL="",
    )
    def test_transactional_email_buttons_use_default_public_webapp_url_in_production(self) -> None:
        invitation = TeamInvitation.objects.create(
            team=self.team,
            email="invitee@example.com",
            role=Membership.Role.MANAGER,
            invited_by=self.owner,
            expires_at=timezone.now() + timedelta(days=7),
        )

        invite_payload = build_team_invite_email_payload(invitation=invitation)
        welcome_payload = build_welcome_email_payload(user=self.member)

        self.assertEqual(
            invite_payload.context["button_url"],
            f"https://worknested.netlify.app/invitations/{invitation.token}",
        )
        self.assertEqual(
            welcome_payload.context["button_url"],
            "https://worknested.netlify.app/dashboard",
        )
        self.assertNotIn("http://localhost:5173", invite_payload.context["button_url"])
        self.assertNotIn("http://localhost:5173", welcome_payload.context["button_url"])

    @override_settings(WELCOME_EMAIL_ENABLED=True)
    def test_welcome_email_can_be_queued(self) -> None:
        user = User.objects.create_user(email="new@example.com", password="StrongPass123!", name="New User")

        delivery = queue_welcome_email(user=user, actor=user)
        delivery.refresh_from_db()

        self.assertEqual(delivery.status, EmailDelivery.Status.SENT)
        self.assertEqual(delivery.email_type, "welcome")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Welcome to", mail.outbox[0].subject)

    @override_settings(
        EMAIL_DELIVERY_MODE="async",
        CELERY_TASK_ALWAYS_EAGER=False,
        WELCOME_EMAIL_ENABLED=True,
    )
    @patch("apps.integrations.email.tasks.deliver_email_task.delay", side_effect=RuntimeError("broker unavailable"))
    def test_email_queue_falls_back_to_inline_delivery_when_broker_is_unavailable(self, _delay_mock) -> None:
        user = User.objects.create_user(email="fallback@example.com", password="StrongPass123!", name="Fallback User")

        with self.captureOnCommitCallbacks(execute=True):
            delivery = queue_welcome_email(user=user, actor=user)
        delivery.refresh_from_db()

        self.assertEqual(delivery.status, EmailDelivery.Status.SENT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Welcome to", mail.outbox[0].subject)

    @override_settings(
        EMAIL_DELIVERY_MODE="sync",
        CELERY_TASK_ALWAYS_EAGER=False,
        WELCOME_EMAIL_ENABLED=True,
    )
    @patch("apps.integrations.email.services.threading.Thread")
    def test_sync_email_queue_schedules_background_delivery_without_blocking_request(self, thread_mock) -> None:
        user = User.objects.create_user(email="background@example.com", password="StrongPass123!", name="Background User")

        with self.captureOnCommitCallbacks(execute=True):
            delivery = queue_welcome_email(user=user, actor=user)
        delivery.refresh_from_db()

        thread_mock.assert_called_once()
        thread_mock.return_value.start.assert_called_once()
        self.assertEqual(delivery.status, EmailDelivery.Status.QUEUED)

    def test_duplicate_dedupe_key_reuses_existing_delivery(self) -> None:
        invitation = TeamInvitation.objects.create(
            team=self.team,
            email="invitee@example.com",
            role=Membership.Role.MANAGER,
            invited_by=self.owner,
            expires_at=timezone.now() + timedelta(days=7),
        )

        first = queue_team_invite_email(invitation=invitation, actor=self.owner)
        second = queue_team_invite_email(invitation=invitation, actor=self.owner)

        self.assertEqual(first.id, second.id)
        self.assertEqual(EmailDelivery.objects.count(), 1)

    def test_failed_delivery_is_tracked_without_crashing(self) -> None:
        user = User.objects.create_user(email="failing@example.com", password="StrongPass123!", name="Failing User")

        with patch(
            "apps.integrations.email.services.send_system_email",
            side_effect=EmailSendFailedError("Temporary outage"),
        ):
            delivery = queue_password_reset_email(
                user=user,
                reset_url="http://localhost:5173/reset-password?uid=test&token=abc",
                actor=user,
            )

        delivery.refresh_from_db()
        self.assertEqual(delivery.status, EmailDelivery.Status.FAILED)
        self.assertEqual(delivery.attempt_count, 1)
        self.assertIn("Temporary outage", delivery.last_error)
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(EMAIL_PROVIDER="sendgrid", SENDGRID_API_KEY="api-key", DEFAULT_FROM_EMAIL="no-reply@example.com")
    def test_sendgrid_provider_posts_expected_payload(self) -> None:
        captured = {}

        def fake_urlopen(request, timeout=30):
            captured["url"] = request.full_url
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            captured["headers"] = dict(request.header_items())
            return DummySendGridResponse()

        with patch("apps.integrations.email.sendgrid.urlopen", side_effect=fake_urlopen):
            result = send_system_email(
                payload=EmailMessagePayload(
                    to=["person@example.com"],
                    subject="SendGrid test",
                    text_body="Body",
                    html_body="<p>Body</p>",
                    metadata={"delivery_id": "123"},
                )
            )

        self.assertEqual(result["provider"], "sendgrid")
        self.assertEqual(captured["url"], SendGridEmailProvider.api_url)
        self.assertEqual(captured["payload"]["subject"], "SendGrid test")
        self.assertEqual(captured["payload"]["personalizations"][0]["to"][0]["email"], "person@example.com")
        self.assertEqual(captured["payload"]["custom_args"]["delivery_id"], "123")
