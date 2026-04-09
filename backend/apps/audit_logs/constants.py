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
    PHONE_UPDATED = "phone_updated", "Phone Updated"
    PHONE_VERIFIED = "phone_verified", "Phone Verified"
    SMS_PREFERENCES_UPDATED = "sms_preferences_updated", "SMS Preferences Updated"

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
    TASK_LABEL_CREATED = "task_label_created", "Task Label Created"
    TASK_LABEL_ATTACHED = "task_label_attached", "Task Label Attached"
    TASK_LABEL_DETACHED = "task_label_detached", "Task Label Detached"
    TASK_CHECKLIST_CREATED = "task_checklist_created", "Task Checklist Created"
    TASK_CHECKLIST_UPDATED = "task_checklist_updated", "Task Checklist Updated"
    TASK_CHECKLIST_DELETED = "task_checklist_deleted", "Task Checklist Deleted"
    TASK_WATCHER_ADDED = "task_watcher_added", "Task Watcher Added"
    TASK_WATCHER_REMOVED = "task_watcher_removed", "Task Watcher Removed"
    TASK_BULK_UPDATED = "task_bulk_updated", "Task Bulk Updated"
    TASK_FAVORITED = "task_favorited", "Task Favorited"
    TASK_UNFAVORITED = "task_unfavorited", "Task Unfavorited"

    COMMENT_CREATED = "comment_created", "Comment Created"
    COMMENT_UPDATED = "comment_updated", "Comment Updated"
    COMMENT_DELETED = "comment_deleted", "Comment Deleted"

    ATTACHMENT_UPLOADED = "attachment_uploaded", "Attachment Uploaded"
    ATTACHMENT_DELETED = "attachment_deleted", "Attachment Deleted"

    EMAIL_QUEUED = "email_queued", "Email Queued"
    EMAIL_SENT = "email_sent", "Email Sent"
    EMAIL_FAILED = "email_failed", "Email Failed"
    EMAIL_SKIPPED = "email_skipped", "Email Skipped"
    SMS_QUEUED = "sms_queued", "SMS Queued"
    SMS_SENT = "sms_sent", "SMS Sent"
    SMS_FAILED = "sms_failed", "SMS Failed"
    ADMIN_SMS_BROADCAST_CREATED = "admin_sms_broadcast_created", "Admin SMS Broadcast Created"
    ADMIN_SMS_BROADCAST_SENT = "admin_sms_broadcast_sent", "Admin SMS Broadcast Sent"

    NOTIFICATION_MARKED_READ = "notification_marked_read", "Notification Marked Read"
    NOTIFICATION_MARKED_UNREAD = "notification_marked_unread", "Notification Marked Unread"
    NOTIFICATIONS_MARKED_READ = "notifications_marked_read", "Notifications Marked Read"
    NOTIFICATION_DELETED = "notification_deleted", "Notification Deleted"
    ADMIN_NOTIFICATION_SENT = "admin_notification_sent", "Admin Notification Sent"
    TEAM_ANNOUNCEMENT_CREATED = "team_announcement_created", "Team Announcement Created"
    TEAM_ANNOUNCEMENT_UPDATED = "team_announcement_updated", "Team Announcement Updated"
    TEAM_PINNED = "team_pinned", "Team Pinned"
    TEAM_UNPINNED = "team_unpinned", "Team Unpinned"
