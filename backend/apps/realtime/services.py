from __future__ import annotations

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.realtime.constants import (
    COMMENT_CREATED_EVENT,
    COMMENT_DELETED_EVENT,
    COMMENT_UPDATED_EVENT,
    NOTIFICATION_CREATED_EVENT,
    NOTIFICATION_DELETED_EVENT,
    NOTIFICATION_UNREAD_COUNT_EVENT,
    NOTIFICATION_UPDATED_EVENT,
    TASK_ARCHIVED_EVENT,
    TASK_ASSIGNED_EVENT,
    TASK_CREATED_EVENT,
    TASK_DELETED_EVENT,
    TASK_STATUS_CHANGED_EVENT,
    TASK_UPDATED_EVENT,
    TEAM_INVITE_RECEIVED_EVENT,
    build_team_group_name,
    build_user_group_name,
)
from apps.realtime.events import ALL_REALTIME_EVENTS, TEAM_SCOPED_EVENTS, USER_SCOPED_EVENTS, build_event_message
from apps.realtime.serializers import (
    build_comment_event_data,
    build_notification_event_data,
    build_task_event_data,
    build_task_status_changed_event_data,
    build_team_invite_event_data,
    build_unread_count_event_data,
)

logger = logging.getLogger(__name__)


def _dispatch_group_event(*, group_name: str, event_name: str, data: dict) -> None:
    if event_name not in ALL_REALTIME_EVENTS:
        raise ValueError(f"Unsupported realtime event: {event_name}")

    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            build_event_message(event_name=event_name, data=data),
        )
    except Exception:  # pragma: no cover
        logger.exception(
            "realtime_event_delivery_failed",
            extra={"group_name": group_name, "event_name": event_name},
        )


def send_user_event(*, user_id, event_name: str, payload: dict) -> None:
    if event_name not in USER_SCOPED_EVENTS:
        raise ValueError(f"User channel cannot receive event: {event_name}")
    _dispatch_group_event(
        group_name=build_user_group_name(user_id),
        event_name=event_name,
        data=payload,
    )


def send_team_event(*, team_id, event_name: str, payload: dict) -> None:
    if event_name not in TEAM_SCOPED_EVENTS:
        raise ValueError(f"Team channel cannot receive event: {event_name}")
    _dispatch_group_event(
        group_name=build_team_group_name(team_id),
        event_name=event_name,
        data=payload,
    )


def send_notification_event(*, notification, event_name: str = NOTIFICATION_CREATED_EVENT) -> None:
    send_user_event(
        user_id=notification.user_id,
        event_name=event_name,
        payload=build_notification_event_data(notification=notification),
    )


def send_notification_deleted_event(*, user_id, notification_id) -> None:
    send_user_event(
        user_id=user_id,
        event_name=NOTIFICATION_DELETED_EVENT,
        payload={"id": str(notification_id)},
    )


def send_unread_count_event(*, user) -> None:
    from apps.notifications.selectors import get_unread_count

    send_user_event(
        user_id=user.id,
        event_name=NOTIFICATION_UNREAD_COUNT_EVENT,
        payload=build_unread_count_event_data(unread_count=get_unread_count(user=user)),
    )


def send_task_created_event(*, task) -> None:
    send_team_event(
        team_id=task.team_id,
        event_name=TASK_CREATED_EVENT,
        payload=build_task_event_data(task=task),
    )


def send_task_update_event(*, task) -> None:
    send_team_event(
        team_id=task.team_id,
        event_name=TASK_UPDATED_EVENT,
        payload=build_task_event_data(task=task),
    )


def send_task_status_changed_event(*, task, previous_status: str, changed_by=None) -> None:
    send_team_event(
        team_id=task.team_id,
        event_name=TASK_STATUS_CHANGED_EVENT,
        payload=build_task_status_changed_event_data(task=task, previous_status=previous_status, changed_by=changed_by),
    )


def send_task_assignment_event(*, task, actor=None) -> None:
    payload = build_task_event_data(task=task)
    if task.assigned_to_id:
        send_user_event(
            user_id=task.assigned_to_id,
            event_name=TASK_ASSIGNED_EVENT,
            payload=payload,
        )
    send_team_event(
        team_id=task.team_id,
        event_name=TASK_ASSIGNED_EVENT,
        payload=payload,
    )


def send_task_archived_event(*, task) -> None:
    send_team_event(
        team_id=task.team_id,
        event_name=TASK_ARCHIVED_EVENT,
        payload=build_task_event_data(task=task),
    )


def send_task_deleted_event(*, task) -> None:
    send_team_event(
        team_id=task.team_id,
        event_name=TASK_DELETED_EVENT,
        payload=build_task_event_data(task=task),
    )


def send_comment_event(*, comment, event_name: str = COMMENT_CREATED_EVENT) -> None:
    send_team_event(
        team_id=comment.task.team_id,
        event_name=event_name,
        payload=build_comment_event_data(comment=comment),
    )


def send_team_invite_event(*, invitation, recipient_user) -> None:
    if recipient_user is None:
        return
    send_user_event(
        user_id=recipient_user.id,
        event_name=TEAM_INVITE_RECEIVED_EVENT,
        payload=build_team_invite_event_data(invitation=invitation),
    )
