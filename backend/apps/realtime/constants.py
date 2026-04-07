from __future__ import annotations

NOTIFICATION_CREATED_EVENT = "notification.created"
NOTIFICATION_UPDATED_EVENT = "notification.updated"
NOTIFICATION_DELETED_EVENT = "notification.deleted"
NOTIFICATION_UNREAD_COUNT_EVENT = "notification.unread_count"

TASK_CREATED_EVENT = "task.created"
TASK_UPDATED_EVENT = "task.updated"
TASK_STATUS_CHANGED_EVENT = "task.status_changed"
TASK_ASSIGNED_EVENT = "task.assigned"
TASK_ARCHIVED_EVENT = "task.archived"
TASK_DELETED_EVENT = "task.deleted"

COMMENT_CREATED_EVENT = "comment.created"
COMMENT_UPDATED_EVENT = "comment.updated"
COMMENT_DELETED_EVENT = "comment.deleted"

TEAM_INVITE_RECEIVED_EVENT = "team.invite_received"
SYSTEM_PONG_EVENT = "system.pong"

USER_GROUP_PREFIX = "user"
TEAM_GROUP_PREFIX = "team"


def build_user_group_name(user_id) -> str:
    return f"{USER_GROUP_PREFIX}_{user_id}"


def build_team_group_name(team_id) -> str:
    return f"{TEAM_GROUP_PREFIX}_{team_id}"
