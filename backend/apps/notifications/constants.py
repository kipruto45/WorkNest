from __future__ import annotations

from django.db import models

from apps.realtime.constants import (
    NOTIFICATION_CREATED_EVENT,
    NOTIFICATION_DELETED_EVENT,
    NOTIFICATION_UNREAD_COUNT_EVENT,
    NOTIFICATION_UPDATED_EVENT,
)


class NotificationType(models.TextChoices):
    TASK_ASSIGNED = "task_assigned", "Task Assigned"
    DEADLINE_APPROACHING = "deadline_approaching", "Deadline Approaching"
    COMMENT_POSTED = "comment_posted", "Comment Posted"
    MENTIONED_IN_COMMENT = "mentioned_in_comment", "Mentioned In Comment"
    TEAM_INVITE = "team_invite", "Team Invite"
    INVITATION_ACCEPTED = "invitation_accepted", "Invitation Accepted"
    INVITATION_DECLINED = "invitation_declined", "Invitation Declined"
    ADMIN_MESSAGE = "admin_message", "Admin Message"
