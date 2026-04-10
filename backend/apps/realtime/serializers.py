from __future__ import annotations

from rest_framework import serializers


class RealtimeUserSummarySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField(allow_blank=True)
    email = serializers.EmailField()
    avatar = serializers.CharField(allow_blank=True, allow_null=True)


class RealtimeEnvelopeSerializer(serializers.Serializer):
    event = serializers.CharField()
    data = serializers.DictField()


class RealtimeUnreadCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField(min_value=0)


class RealtimeTaskSerializer(serializers.Serializer):
    task_id = serializers.UUIDField(source="id")
    team_id = serializers.UUIDField()
    title = serializers.CharField()
    status = serializers.CharField()
    priority = serializers.CharField()
    assigned_to = serializers.UUIDField(allow_null=True)
    due_date = serializers.DateTimeField(allow_null=True)
    position = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class RealtimeTaskStatusSerializer(RealtimeTaskSerializer):
    previous_status = serializers.CharField()
    changed_by = RealtimeUserSummarySerializer(allow_null=True)


class RealtimeCommentSerializer(serializers.Serializer):
    comment_id = serializers.UUIDField(source="id")
    task_id = serializers.UUIDField()
    team_id = serializers.UUIDField()
    parent_id = serializers.UUIDField(allow_null=True)
    content = serializers.CharField()
    is_deleted = serializers.BooleanField()
    author = RealtimeUserSummarySerializer(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class RealtimeTeamInviteSerializer(serializers.Serializer):
    invitation_id = serializers.UUIDField(source="id")
    team_id = serializers.UUIDField(source="team_id")
    team_name = serializers.CharField(source="team.name")
    team_slug = serializers.CharField(source="team.slug")
    role = serializers.CharField()
    token = serializers.CharField(source="token")
    invited_by = RealtimeUserSummarySerializer(source="invited_by", allow_null=True)
    expires_at = serializers.DateTimeField()


def _serialize_user(user) -> dict | None:
    if user is None:
        return None
    return RealtimeUserSummarySerializer(user).data


def build_unread_count_event_data(*, unread_count: int) -> dict:
    return RealtimeUnreadCountSerializer({"unread_count": unread_count}).data


def build_notification_event_data(*, notification) -> dict:
    from apps.notifications.serializers import NotificationListSerializer

    return NotificationListSerializer(notification).data


def build_task_event_data(*, task) -> dict:
    payload = {
        "id": task.id,
        "team_id": task.team_id,
        "title": task.title,
        "status": task.status,
        "priority": task.priority,
        "assigned_to": task.assigned_to_id,
        "due_date": task.due_date,
        "position": task.position,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
    }
    return RealtimeTaskSerializer(payload).data


def build_task_status_changed_event_data(*, task, previous_status: str, changed_by=None) -> dict:
    payload = {
        "id": task.id,
        "team_id": task.team_id,
        "title": task.title,
        "status": task.status,
        "priority": task.priority,
        "assigned_to": task.assigned_to_id,
        "due_date": task.due_date,
        "position": task.position,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "previous_status": previous_status,
        "changed_by": _serialize_user(changed_by),
    }
    return RealtimeTaskStatusSerializer(payload).data


def build_comment_event_data(*, comment) -> dict:
    payload = {
        "id": comment.id,
        "task_id": comment.task_id,
        "team_id": comment.task.team_id,
        "parent_id": comment.parent_id,
        "content": comment.content,
        "is_deleted": comment.is_deleted,
        "author": _serialize_user(comment.author),
        "created_at": comment.created_at,
        "updated_at": comment.updated_at,
    }
    return RealtimeCommentSerializer(payload).data


def build_team_invite_event_data(*, invitation) -> dict:
    return RealtimeTeamInviteSerializer(invitation).data
