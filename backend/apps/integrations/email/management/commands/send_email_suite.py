from __future__ import annotations

from dataclasses import replace
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.attachments.models import Attachment
from apps.comments.models import Comment
from apps.integrations.email.builders import (
    build_attachment_uploaded_email_payload,
    build_comment_posted_email_payload,
    build_deadline_approaching_email_payload,
    build_invitation_accepted_email_payload,
    build_invitation_reminder_email_payload,
    build_invitation_revoked_email_payload,
    build_mentioned_email_payload,
    build_notification_email_payload,
    build_password_reset_email_payload,
    build_role_changed_email_payload,
    build_task_assigned_email_payload,
    build_task_status_changed_email_payload,
    build_team_invite_email_payload,
    build_welcome_email_payload,
)
from apps.integrations.email.services import deliver_prepared_email
from apps.memberships.models import Membership, TeamInvitation
from apps.notifications.constants import NotificationType
from apps.notifications.models import Notification
from apps.tasks.models import Task
from apps.teams.services import create_team_with_owner
from apps.users.models import User


class Command(BaseCommand):
    help = "Send the full WorkNest event email suite to a single inbox using the configured email backend."

    def add_arguments(self, parser):
        parser.add_argument("--to", required=True, help="Recipient email address for all test emails.")
        parser.add_argument(
            "--prefix",
            default="[WorkNest Email Test]",
            help="Subject prefix to make the test emails easy to identify.",
        )

    def handle(self, *args, **options):
        recipient_email = str(options["to"]).strip().lower()
        subject_prefix = str(options["prefix"]).strip()
        if not recipient_email:
            raise CommandError("A recipient email is required.")

        sent_types: list[str] = []

        with transaction.atomic():
            owner = User.objects.create_user(
                email="suite-owner@worknest.local",
                password="WorkNest123!",
                name="Suite Owner",
                first_name="Suite",
                last_name="Owner",
                email_verified=True,
            )
            recipient = User.objects.create_user(
                email=recipient_email,
                password="WorkNest123!",
                name="Email Test Recipient",
                first_name="Email",
                last_name="Recipient",
                email_verified=True,
            )
            reviewer = User.objects.create_user(
                email="suite-reviewer@worknest.local",
                password="WorkNest123!",
                name="Suite Reviewer",
                first_name="Suite",
                last_name="Reviewer",
                email_verified=True,
            )

            team = create_team_with_owner(
                created_by=owner,
                name="Email QA Workspace",
                description="Temporary workspace for outbound email verification.",
                allow_manager_invites=True,
            )

            membership = Membership.objects.create(
                team=team,
                user=recipient,
                role=Membership.Role.MEMBER,
                status=Membership.Status.ACTIVE,
                invited_by=owner,
                joined_at=timezone.now(),
            )

            invitation = TeamInvitation.objects.create(
                team=team,
                email=recipient_email,
                role=Membership.Role.MANAGER,
                invited_by=owner,
                custom_message="Welcome to the email verification workspace.",
                expires_at=timezone.now() + timedelta(days=7),
            )

            task = Task.objects.create(
                team=team,
                title="Verify outbound email notifications",
                description="Confirm that SMTP can deliver all WorkNest event emails.",
                assigned_to=recipient,
                created_by=owner,
                priority=Task.Priority.HIGH,
                status=Task.Status.IN_PROGRESS,
                due_date=timezone.now() + timedelta(days=2),
            )
            task.last_status_changed_by = owner
            task.last_status_changed_at = timezone.now()
            task.save(update_fields=["last_status_changed_by", "last_status_changed_at", "updated_at"])

            comment = Comment.objects.create(
                task=task,
                author=owner,
                content="Please confirm you received the email test messages.",
            )
            attachment = Attachment.objects.create(
                task=task,
                uploaded_by=owner,
                original_name="email-suite-checklist.pdf",
                file_name="email-suite-checklist.pdf",
                file_path="attachments/email-suite-checklist.pdf",
                file_url="https://worknest-backend-t6dw.onrender.com/files/attachments/email-suite-checklist.pdf",
                file_size=2048,
                mime_type="application/pdf",
            )

            generic_notification = Notification.objects.create(
                user=recipient,
                actor=owner,
                type=NotificationType.ADMIN_MESSAGE,
                title="WorkNest email suite test",
                message="This is the generic notification email fallback test.",
                team=team,
                metadata={"source": "management.send_email_suite"},
                target_type="notification",
            )

            payloads = [
                build_password_reset_email_payload(
                    user=recipient,
                    reset_url="https://work-nest-lemon.vercel.app/reset-password?uid=test-user&token=test-token",
                ),
                build_team_invite_email_payload(invitation=invitation),
                build_invitation_reminder_email_payload(invitation=invitation),
                build_invitation_revoked_email_payload(invitation=invitation, actor=owner),
                build_task_assigned_email_payload(task=task, assigner=owner, assignee=recipient),
                build_deadline_approaching_email_payload(task=task, recipient=recipient, reminder_window_hours=24),
                build_comment_posted_email_payload(comment=comment, task=task, recipient=recipient),
                build_mentioned_email_payload(comment=comment, task=task, mentioned_user=recipient),
                build_welcome_email_payload(user=recipient),
                build_invitation_accepted_email_payload(invitation=invitation, recipient_user=owner, actor=recipient),
                build_role_changed_email_payload(
                    membership=membership,
                    actor=owner,
                    old_role=Membership.Role.MEMBER,
                    new_role=Membership.Role.MANAGER,
                ),
                build_task_status_changed_email_payload(
                    task=task,
                    previous_status=Task.Status.TODO,
                    changed_by=reviewer,
                    recipient=recipient,
                ),
                build_attachment_uploaded_email_payload(attachment=attachment, recipient=recipient),
                build_notification_email_payload(notification=generic_notification),
            ]

            for payload in payloads:
                prepared_payload = replace(
                    payload,
                    recipient_email=recipient_email,
                    subject=f"{subject_prefix} {payload.subject}" if subject_prefix else payload.subject,
                    dedupe_key="",
                )
                deliver_prepared_email(payload=prepared_payload)
                sent_types.append(prepared_payload.email_type)
                self.stdout.write(f"sent={prepared_payload.email_type} to={recipient_email}")

            transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"Delivered {len(sent_types)} email tests to {recipient_email}: {', '.join(sent_types)}"
            )
        )
