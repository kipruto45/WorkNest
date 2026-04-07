from __future__ import annotations

from django.db import models

AUDIT_REDACTED_VALUE = "[REDACTED]"
AUDIT_SENSITIVE_METADATA_KEYS = {
    "access",
    "access_token",
    "authorization",
    "cookie",
    "password",
    "refresh",
    "refresh_token",
    "secret",
    "token",
    "api_key",
    "key",
}


class AuditAction(models.TextChoices):
    USER_REGISTERED = "user_registered", "User Registered"
    USER_LOGGED_IN = "user_logged_in", "User Logged In"
    USER_LOGGED_OUT = "user_logged_out", "User Logged Out"
    USER_LOGIN_FAILED = "user_login_failed", "User Login Failed"
    PASSWORD_RESET_REQUESTED = "password_reset_requested", "Password Reset Requested"
    PASSWORD_RESET_CONFIRMED = "password_reset_confirmed", "Password Reset Confirmed"
    GOOGLE_LOGIN_REQUESTED = "google_login_requested", "Google Login Requested"
    ACCOUNT_LINKED = "account_linked", "Account Linked"

    TEAM_CREATED = "team_created", "Team Created"
    TEAM_UPDATED = "team_updated", "Team Updated"
    TEAM_ARCHIVED = "team_archived", "Team Archived"
    TEAM_DELETED = "team_deleted", "Team Deleted"

    MEMBER_INVITED = "member_invited", "Member Invited"
    INVITATION_RESENT = "invitation_resent", "Invitation Resent"
    INVITATION_REVOKED = "invitation_revoked", "Invitation Revoked"
    INVITATION_ACCEPTED = "invitation_accepted", "Invitation Accepted"
    INVITATION_DECLINED = "invitation_declined", "Invitation Declined"
    INVITATION_ROLE_UPDATED = "invitation_role_updated", "Invitation Role Updated"
    MEMBER_ROLE_CHANGED = "member_role_changed", "Member Role Changed"
    MEMBER_REMOVED = "member_removed", "Member Removed"

    TASK_CREATED = "task_created", "Task Created"
    TASK_UPDATED = "task_updated", "Task Updated"
    TASK_ASSIGNED = "task_assigned", "Task Assigned"
    TASK_STATUS_CHANGED = "task_status_changed", "Task Status Changed"
    TASK_ARCHIVED = "task_archived", "Task Archived"
    TASK_DELETED = "task_deleted", "Task Deleted"

    COMMENT_CREATED = "comment_created", "Comment Created"
    COMMENT_UPDATED = "comment_updated", "Comment Updated"
    COMMENT_DELETED = "comment_deleted", "Comment Deleted"

    ATTACHMENT_UPLOADED = "attachment_uploaded", "Attachment Uploaded"
    ATTACHMENT_DELETED = "attachment_deleted", "Attachment Deleted"

    EMAIL_QUEUED = "email_queued", "Email Queued"
    EMAIL_SENT = "email_sent", "Email Sent"
    EMAIL_FAILED = "email_failed", "Email Failed"
    EMAIL_SKIPPED = "email_skipped", "Email Skipped"

    NOTIFICATION_MARKED_READ = "notification_marked_read", "Notification Marked Read"
    NOTIFICATION_MARKED_UNREAD = "notification_marked_unread", "Notification Marked Unread"
    NOTIFICATIONS_MARKED_READ = "notifications_marked_read", "Notifications Marked Read"
    NOTIFICATION_DELETED = "notification_deleted", "Notification Deleted"
    ADMIN_NOTIFICATION_SENT = "admin_notification_sent", "Admin Notification Sent"
