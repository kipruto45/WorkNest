from __future__ import annotations

from django.db.models import QuerySet

from apps.notifications.models import Notification


def _parse_bool(value):
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes"}


def get_user_notifications(*, user, is_read=None, notification_type=None, team_id=None) -> QuerySet[Notification]:
    queryset = Notification.objects.filter(user=user).select_related("actor", "team")
    parsed_is_read = _parse_bool(is_read)
    if parsed_is_read is not None:
        queryset = queryset.filter(is_read=parsed_is_read)
    if notification_type:
        queryset = queryset.filter(type=notification_type)
    if team_id:
        queryset = queryset.filter(team_id=team_id)
    return queryset.order_by("-created_at")


def get_unread_notifications(*, user) -> QuerySet[Notification]:
    return get_user_notifications(user=user, is_read=False)


def get_notification_for_user(*, notification_id, user) -> Notification | None:
    return get_user_notifications(user=user).filter(id=notification_id).first()


def get_unread_count(*, user) -> int:
    return Notification.objects.filter(user=user, is_read=False).count()


def get_recent_notifications(*, user, limit: int = 20) -> QuerySet[Notification]:
    return get_user_notifications(user=user)[:limit]
