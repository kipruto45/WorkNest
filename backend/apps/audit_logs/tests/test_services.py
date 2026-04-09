from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings

from apps.attachments.services import delete_attachment, upload_attachment
from apps.audit_logs.constants import AUDIT_REDACTED_VALUE, AuditAction
from apps.audit_logs.middleware import clear_current_audit_request_context, set_current_audit_request_context
from apps.audit_logs.models import AuditLog
from apps.audit_logs.services import create_audit_log
from apps.audit_logs.tests.utils import AuditLogFixtureMixin, TemporaryAuditMediaRootMixin
from apps.authentication.services import authenticate_user, confirm_password_reset, create_user_account, request_password_reset
from apps.comments.services import delete_comment
from apps.memberships.models import TeamInvitation
from apps.memberships.services import accept_team_invitation, change_member_role, invite_member_to_team
from apps.notifications.constants import NotificationType
from apps.notifications.models import Notification
from apps.notifications.services import delete_notification, mark_all_notifications_read, mark_notification_as_read, mark_notification_as_unread
from apps.tasks.services import assign_task, change_task_status, create_task, update_task


class AuditLogServiceTests(TemporaryAuditMediaRootMixin, AuditLogFixtureMixin, TestCase):
    def test_create_audit_log_sanitizes_sensitive_metadata_and_captures_request_context(self) -> None:
        request = RequestFactory().get("/", HTTP_USER_AGENT="Audit Test Agent", REMOTE_ADDR="127.0.0.1")
        set_current_audit_request_context(request=request)
        try:
            audit_log = create_audit_log(
                actor=self.owner,
                action=AuditAction.TASK_CREATED,
                target=self.task,
                metadata={"password": "secret", "refresh_token": "token", "safe": "value"},
            )
        finally:
            clear_current_audit_request_context()

        self.assertEqual(audit_log.team, self.team)
        self.assertEqual(audit_log.ip_address, "127.0.0.1")
        self.assertEqual(audit_log.user_agent, "Audit Test Agent")
        self.assertEqual(audit_log.metadata["password"], AUDIT_REDACTED_VALUE)
        self.assertEqual(audit_log.metadata["refresh_token"], AUDIT_REDACTED_VALUE)
        self.assertEqual(audit_log.metadata["safe"], "value")

    def test_team_and_membership_services_create_audit_logs(self) -> None:
        invitation = invite_member_to_team(
            team=self.team,
            invited_by=self.owner,
            email="invitee@example.com",
            role="member",
        )

        self.assertTrue(AuditLog.objects.filter(action=AuditAction.MEMBER_INVITED, target_id=str(invitation.id)).exists())

        invited_user = create_user_account(name="Invitee", email="invitee@example.com", password="StrongPass123!")
        invitation = TeamInvitation.objects.get(pk=invitation.pk)
        invitation.email = invited_user.email
        invitation.save(update_fields=["email"])
        accepted_membership = accept_team_invitation(invitation=invitation, user=invited_user)

        self.assertTrue(
            AuditLog.objects.filter(action=AuditAction.INVITATION_ACCEPTED, target_id=str(invitation.id)).exists()
        )

        change_member_role(
            team=self.team,
            actor=self.owner,
            membership=accepted_membership,
            new_role="manager",
        )

        self.assertTrue(
            AuditLog.objects.filter(action=AuditAction.MEMBER_ROLE_CHANGED, target_id=str(accepted_membership.id)).exists()
        )

    def test_task_comment_attachment_and_notification_services_create_audit_logs(self) -> None:
        created_task = create_task(team=self.team, title="New audited task", created_by=self.owner, assigned_to=self.member)
        update_task(task=created_task, actor=self.owner, title="Updated audited task")
        assign_task(task=created_task, user=self.team_admin, actor=self.owner)
        change_task_status(task=created_task, new_status=created_task.Status.IN_PROGRESS, changed_by=self.owner)
        delete_comment(comment=self.comment, actor=self.owner)

        attachment = upload_attachment(
            task=self.task,
            uploaded_by=self.owner,
            file_obj=SimpleUploadedFile(
                "brief.pdf",
                b"%PDF-1.4 audit attachment",
                content_type="application/pdf",
            ),
        )
        delete_attachment(attachment=attachment, deleted_by=self.owner)

        notification = Notification.objects.create(
            user=self.member,
            type=NotificationType.TASK_ASSIGNED,
            title="Task assigned",
            message="You were assigned a task",
            team=self.team,
        )
        notification_id = str(notification.id)
        mark_notification_as_read(notification=notification)
        mark_notification_as_unread(notification=notification)
        mark_all_notifications_read(user=self.member)
        delete_notification(notification=notification)

        self.assertTrue(AuditLog.objects.filter(action=AuditAction.TASK_CREATED, target_id=str(created_task.id)).exists())
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.TASK_UPDATED, target_id=str(created_task.id)).exists())
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.TASK_ASSIGNED, target_id=str(created_task.id)).exists())
        self.assertTrue(
            AuditLog.objects.filter(action=AuditAction.TASK_STATUS_CHANGED, target_id=str(created_task.id)).exists()
        )
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.COMMENT_DELETED, target_id=str(self.comment.id)).exists())
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.ATTACHMENT_UPLOADED, target_id=str(attachment.id)).exists())
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.ATTACHMENT_DELETED, target_id=str(attachment.id)).exists())
        self.assertTrue(
            AuditLog.objects.filter(action=AuditAction.NOTIFICATION_MARKED_READ, target_id=notification_id).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(action=AuditAction.NOTIFICATION_MARKED_UNREAD, target_id=notification_id).exists()
        )
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.NOTIFICATIONS_MARKED_READ, actor=self.member).exists())
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.NOTIFICATION_DELETED, target_id=notification_id).exists())

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="client-id", GOOGLE_OAUTH_CLIENT_SECRET="client-secret")
    def test_authentication_services_create_audit_logs(self) -> None:
        user = create_user_account(
            name="Auth User",
            email="auth@example.com",
            password="StrongPass123!",
            account_type="personal",
        )
        request = RequestFactory().post("/api/v1/auth/login/", HTTP_USER_AGENT="Auth Agent", REMOTE_ADDR="127.0.0.1")
        authenticate_user(email="auth@example.com", password="StrongPass123!", request=request, account_type="personal")
        request_password_reset(email="auth@example.com", request=request)
        confirm_password_reset(user=user, new_password="StrongPass123!Updated")

        self.assertTrue(AuditLog.objects.filter(action=AuditAction.USER_REGISTERED, actor=user).exists())
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.USER_LOGGED_IN, actor=user).exists())
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.PASSWORD_RESET_REQUESTED, actor=user).exists())
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.PASSWORD_RESET_CONFIRMED, actor=user).exists())
