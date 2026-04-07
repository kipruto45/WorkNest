from __future__ import annotations

import logging

from django.conf import settings
from django.db import connection
from django.db import transaction
from django.utils import timezone

from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, log_notification_action
from apps.notifications.constants import (
    NOTIFICATION_CREATED_EVENT,
    NOTIFICATION_DELETED_EVENT,
    NOTIFICATION_UNREAD_COUNT_EVENT,
    NOTIFICATION_UPDATED_EVENT,
    NotificationType,
)
from apps.notifications.models import Notification
from apps.realtime.services import (
    send_notification_deleted_event,
    send_notification_event,
    send_team_invite_event,
    send_unread_count_event,
    send_user_event,
)

logger = logging.getLogger(__name__)


def build_notification_payload(*, notification: Notification) -> dict:
    from apps.notifications.serializers import NotificationListSerializer

    return NotificationListSerializer(notification).data


def _build_unread_count_payload(*, user) -> dict:
    from apps.notifications.selectors import get_unread_count

    return {"unread_count": get_unread_count(user=user)}


def _group_name_for_user(*, user) -> str:
    return f"user_{user.id}"


def send_realtime_event(*, user, event_name: str, data: dict) -> None:
    send_user_event(user_id=user.id, event_name=event_name, payload=data)


def send_realtime_notification(*, notification: Notification, event_name: str = NOTIFICATION_CREATED_EVENT) -> None:
    send_notification_event(
        notification=notification,
        event_name=event_name,
    )


def send_unread_count_update(*, user) -> None:
    send_unread_count_event(user=user)


def should_send_email_for_type(*, notification_type: str) -> bool:
    if not getattr(settings, "NOTIFICATION_EMAIL_ENABLED", True):
        return False
    allowed_types = getattr(
        settings,
        "NOTIFICATION_EMAIL_TYPES",
        [
            NotificationType.TASK_ASSIGNED,
            NotificationType.MENTIONED_IN_COMMENT,
            NotificationType.DEADLINE_APPROACHING,
            NotificationType.COMMENT_POSTED,
        ],
    )
    return notification_type in allowed_types


def queue_email_notification(*, notification: Notification) -> None:
    if not should_send_email_for_type(notification_type=notification.type):
        return
    from apps.integrations.email.services import queue_notification_email

    try:
        queue_notification_email(notification=notification)
    except Exception:  # pragma: no cover
        logger.exception("notification_email_queue_failed", extra={"notification_id": str(notification.id)})


def _dispatch_notification_side_effects(*, notification: Notification, event_name: str) -> None:
    send_realtime_notification(notification=notification, event_name=event_name)
    send_unread_count_update(user=notification.user)
    if event_name == NOTIFICATION_CREATED_EVENT:
        queue_email_notification(notification=notification)


def create_notification(
    *,
    user,
    notification_type: str,
    title: str,
    message: str,
    actor=None,
    team=None,
    metadata: dict | None = None,
    target_type: str = "",
    target_id=None,
    send_email: bool | None = None,
) -> Notification:
    notification = Notification.objects.create(
        user=user,
        type=notification_type,
        title=title,
        message=message,
        actor=actor,
        team=team,
        metadata=metadata or {},
        target_type=target_type,
        target_id=target_id,
    )

    def on_commit() -> None:
        send_notification_event(notification=notification, event_name=NOTIFICATION_CREATED_EVENT)
        send_unread_count_event(user=notification.user)
        if send_email is True or (send_email is None and should_send_email_for_type(notification_type=notification.type)):
            queue_email_notification(notification=notification)

    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) or not connection.in_atomic_block:
        on_commit()
    else:
        transaction.on_commit(on_commit)
    return notification


def create_bulk_notifications(
    *,
    users,
    notification_type: str,
    title: str,
    message_builder,
    actor=None,
    team=None,
    metadata_builder=None,
    target_type: str = "",
    target_id=None,
    send_email: bool | None = None,
) -> list[Notification]:
    notifications: list[Notification] = []
    for user in users:
        notifications.append(
            Notification(
                user=user,
                type=notification_type,
                title=title if isinstance(title, str) else title(user),
                message=message_builder(user) if callable(message_builder) else str(message_builder),
                actor=actor,
                team=team,
                metadata=metadata_builder(user) if callable(metadata_builder) else (metadata_builder or {}),
                target_type=target_type,
                target_id=target_id,
            )
        )
    created = Notification.objects.bulk_create(notifications)

    def on_commit() -> None:
        for notification in created:
            send_notification_event(notification=notification, event_name=NOTIFICATION_CREATED_EVENT)
            send_unread_count_event(user=notification.user)
            if send_email is True or (send_email is None and should_send_email_for_type(notification_type=notification.type)):
                queue_email_notification(notification=notification)

    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) or not connection.in_atomic_block:
        on_commit()
    else:
        transaction.on_commit(on_commit)
    return created


def mark_notification_as_read(*, notification: Notification) -> Notification:
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save(update_fields=["is_read", "read_at"])
        log_notification_action(
            actor=notification.user,
            action=AuditAction.NOTIFICATION_MARKED_READ,
            notification=notification,
            metadata=build_audit_metadata(notification_type=notification.type, title=notification.title),
        )

        transaction.on_commit(
            lambda: (
                send_notification_event(notification=notification, event_name=NOTIFICATION_UPDATED_EVENT),
                send_unread_count_event(user=notification.user),
            )
        )
    return notification


def mark_notification_as_unread(*, notification: Notification) -> Notification:
    if notification.is_read:
        notification.is_read = False
        notification.read_at = None
        notification.save(update_fields=["is_read", "read_at"])
        log_notification_action(
            actor=notification.user,
            action=AuditAction.NOTIFICATION_MARKED_UNREAD,
            notification=notification,
            metadata=build_audit_metadata(notification_type=notification.type, title=notification.title),
        )

        transaction.on_commit(
            lambda: (
                send_notification_event(notification=notification, event_name=NOTIFICATION_UPDATED_EVENT),
                send_unread_count_event(user=notification.user),
            )
        )
    return notification


def mark_all_notifications_read(*, user) -> int:
    unread_notifications = list(Notification.objects.filter(user=user, is_read=False))
    updated_count = Notification.objects.filter(user=user, is_read=False).update(
        is_read=True,
        read_at=timezone.now(),
    )
    if updated_count:
        for notification in unread_notifications:
            notification.is_read = True
            notification.read_at = timezone.now()

        log_notification_action(
            actor=user,
            action=AuditAction.NOTIFICATIONS_MARKED_READ,
            metadata=build_audit_metadata(updated_count=updated_count),
            target_repr="All notifications",
            target_type="notifications",
        )

        def on_commit() -> None:
            for notification in unread_notifications:
                send_notification_event(notification=notification, event_name=NOTIFICATION_UPDATED_EVENT)
            send_unread_count_event(user=user)

        transaction.on_commit(on_commit)
    return updated_count


def delete_notification(*, notification: Notification) -> None:
    user = notification.user
    notification_id = str(notification.id)
    was_unread = not notification.is_read
    log_notification_action(
        actor=user,
        action=AuditAction.NOTIFICATION_DELETED,
        notification=notification,
        metadata=build_audit_metadata(notification_type=notification.type, title=notification.title),
    )
    notification.delete()

    def on_commit() -> None:
        send_notification_deleted_event(
            user_id=user.id,
            notification_id=notification_id,
        )
        if was_unread:
            send_unread_count_event(user=user)

    transaction.on_commit(on_commit)


def send_admin_notifications(*, actor, scope: str, message: str, title: str = "", user_ids: list | None = None) -> dict:
    from apps.users.models import User

    normalized_title = (title or "").strip() or "Message from admin"
    normalized_message = message.strip()
    requested_user_ids = [str(user_id) for user_id in (user_ids or [])]

    queryset = User.objects.filter(is_active=True, is_staff=False).exclude(id=getattr(actor, "id", None))
    if scope == "selected":
        queryset = queryset.filter(id__in=requested_user_ids)

    recipients = list(queryset.order_by("name", "email"))

    if not recipients:
        return {"count": 0, "recipient_ids": [], "scope": scope}

    def metadata_builder(_user):
        return {
            "delivery_scope": scope,
            "sender_id": str(actor.id),
            "sender_name": getattr(actor, "name", "") or getattr(actor, "email", "Admin"),
            "audience": "all_users" if scope == "all" else "selected_users",
        }

    created = create_bulk_notifications(
        users=recipients,
        notification_type=NotificationType.ADMIN_MESSAGE,
        title=normalized_title,
        message_builder=normalized_message,
        actor=actor,
        metadata_builder=metadata_builder,
        target_type="admin_notification",
        send_email=False,
    )

    log_notification_action(
        actor=actor,
        action=AuditAction.ADMIN_NOTIFICATION_SENT,
        metadata=build_audit_metadata(
            scope=scope,
            title=normalized_title,
            message_preview=normalized_message[:120],
            recipient_count=len(created),
            recipient_ids=[str(user.id) for user in recipients[:100]],
        ),
        target_repr=normalized_title,
        target_type="admin_notification",
    )

    return {
        "count": len(created),
        "recipient_ids": [str(user.id) for user in recipients],
        "scope": scope,
    }


def notify_task_assignment(*, task, actor) -> Notification | None:
    assignee = task.assigned_to
    if assignee is None or (actor and assignee.id == actor.id):
        return None
    return create_notification(
        user=assignee,
        notification_type=NotificationType.TASK_ASSIGNED,
        title="Task assigned to you",
        message=f"{actor.name if actor else 'A teammate'} assigned '{task.title}' to you.",
        actor=actor,
        team=task.team,
        metadata={
            "task_id": str(task.id),
            "team_id": str(task.team_id),
            "team_slug": task.team.slug,
        },
        target_type="task",
        target_id=task.id,
    )


def notify_team_invite(*, invitation, recipient_user) -> Notification | None:
    if recipient_user is None:
        return None
    notification = create_notification(
        user=recipient_user,
        notification_type=NotificationType.TEAM_INVITE,
        title="You received a team invitation",
        message=f"{invitation.invited_by.name if invitation.invited_by else 'A teammate'} invited you to join {invitation.team.name} as a {invitation.role}.",
        actor=invitation.invited_by,
        team=invitation.team,
        metadata={
            "team_id": str(invitation.team_id),
            "team_slug": invitation.team.slug,
            "invitation_token": invitation.token,
            "role": invitation.role,
        },
        target_type="team_invitation",
        target_id=invitation.id,
        send_email=False,
    )
    transaction.on_commit(lambda: send_team_invite_event(invitation=invitation, recipient_user=recipient_user))
    return notification


def notify_invitation_accepted(*, invitation, recipient_user) -> Notification | None:
    if recipient_user is None:
        return None
    return create_notification(
        user=recipient_user,
        notification_type=NotificationType.INVITATION_ACCEPTED,
        title="Invitation accepted",
        message=f"{invitation.email} accepted the invitation to join {invitation.team.name}.",
        actor=recipient_user,
        team=invitation.team,
        metadata={
            "team_id": str(invitation.team_id),
            "team_slug": invitation.team.slug,
            "invitation_id": str(invitation.id),
            "email": invitation.email,
            "role": invitation.role,
        },
        target_type="team_invitation",
        target_id=invitation.id,
        send_email=False,
    )


def notify_invitation_declined(*, invitation, recipient_user) -> Notification | None:
    if recipient_user is None:
        return None
    return create_notification(
        user=recipient_user,
        notification_type=NotificationType.INVITATION_DECLINED,
        title="Invitation declined",
        message=f"{invitation.email} declined the invitation to join {invitation.team.name}.",
        actor=recipient_user,
        team=invitation.team,
        metadata={
            "team_id": str(invitation.team_id),
            "team_slug": invitation.team.slug,
            "invitation_id": str(invitation.id),
            "email": invitation.email,
            "role": invitation.role,
        },
        target_type="team_invitation",
        target_id=invitation.id,
        send_email=False,
    )


def _build_comment_participants(*, comment) -> list:
    participant_ids = set()
    participants = []

    for user in [comment.task.created_by, comment.task.assigned_to]:
        if user and user.id not in participant_ids:
            participant_ids.add(user.id)
            participants.append(user)

    comment_authors = (
        comment.task.comments.exclude(author__isnull=True)
        .exclude(author_id__in=participant_ids)
        .select_related("author")
        .values_list("author_id", flat=True)
        .distinct()
    )
    from django.contrib.auth import get_user_model

    User = get_user_model()
    if comment_authors:
        for user in User.objects.filter(id__in=comment_authors):
            if user.id not in participant_ids:
                participant_ids.add(user.id)
                participants.append(user)
    return participants


def notify_comment_activity(*, comment, mentions: list | None = None) -> list[Notification]:
    from apps.integrations.email.services import send_comment_posted_email, send_mentioned_email
    
    mentions = [user for user in (mentions or []) if user and user.id != comment.author_id]
    mentioned_ids = {user.id for user in mentions}
    
    email_enabled = getattr(settings, 'NOTIFICATION_EMAIL_ENABLED', True)
    
    mention_notifications: list[Notification] = []
    for user in mentions:
        mention_notifications.append(
            create_notification(
                user=user,
                notification_type=NotificationType.MENTIONED_IN_COMMENT,
                title="You were mentioned in a comment",
                message=f"{comment.author.name if comment.author else 'A teammate'} mentioned you in a comment on '{comment.task.title}'.",
                actor=comment.author,
                team=comment.task.team,
                metadata={
                    "task_id": str(comment.task_id),
                    "comment_id": str(comment.id),
                    "team_id": str(comment.task.team_id),
                },
                target_type="comment",
                target_id=comment.id,
            )
        )
        if email_enabled and hasattr(settings, 'NOTIFICATION_EMAIL_TYPES'):
            notify_types = getattr(settings, 'NOTIFICATION_EMAIL_TYPES', 'task_assigned,mentioned_in_comment,deadline_approaching,comment_posted')
            if 'mentioned_in_comment' in notify_types:
                try:
                    transaction.on_commit(
                        lambda u=user: send_mentioned_email(comment=comment, task=comment.task, mentioned_user=u)
                    )
                except Exception:
                    pass
    
    participant_notifications: list[Notification] = []
    for user in _build_comment_participants(comment=comment):
        if user.id == comment.author_id or user.id in mentioned_ids:
            continue
        participant_notifications.append(
            create_notification(
                user=user,
                notification_type=NotificationType.COMMENT_POSTED,
                title="New comment on a task",
                message=f"{comment.author.name if comment.author else 'A teammate'} commented on '{comment.task.title}'.",
                actor=comment.author,
                team=comment.task.team,
                metadata={
                    "task_id": str(comment.task_id),
                    "comment_id": str(comment.id),
                    "team_id": str(comment.task.team_id),
                },
                target_type="comment",
                target_id=comment.id,
            )
        )
        if email_enabled and hasattr(settings, 'NOTIFICATION_EMAIL_TYPES'):
            notify_types = getattr(settings, 'NOTIFICATION_EMAIL_TYPES', 'task_assigned,mentioned_in_comment,deadline_approaching,comment_posted')
            if 'comment_posted' in notify_types:
                try:
                    transaction.on_commit(
                        lambda u=user: send_comment_posted_email(comment=comment, task=comment.task, recipient=u)
                    )
                except Exception:
                    pass
    
    return mention_notifications + participant_notifications


def notify_comment_mentions(*, comment, mentions: list | None = None) -> list[Notification]:
    mentions = [user for user in (mentions or []) if user and user.id != comment.author_id]
    notifications: list[Notification] = []
    for user in mentions:
        notifications.append(
            create_notification(
                user=user,
                notification_type=NotificationType.MENTIONED_IN_COMMENT,
                title="You were mentioned in a comment",
                message=f"{comment.author.name if comment.author else 'A teammate'} mentioned you in a comment on '{comment.task.title}'.",
                actor=comment.author,
                team=comment.task.team,
                metadata={
                    "task_id": str(comment.task_id),
                    "comment_id": str(comment.id),
                    "team_id": str(comment.task.team_id),
                },
                target_type="comment",
                target_id=comment.id,
            )
        )
    return notifications


def notify_deadline_approaching(*, task, reminder_window_hours: int = 24) -> Notification | None:
    assignee = task.assigned_to
    if assignee is None:
        return None
    already_exists = Notification.objects.filter(
        user=assignee,
        type=NotificationType.DEADLINE_APPROACHING,
        target_type="task",
        target_id=task.id,
        metadata__reminder_window_hours=reminder_window_hours,
    ).exists()
    if already_exists:
        return None
    due_display = timezone.localtime(task.due_date).strftime("%Y-%m-%d %H:%M") if task.due_date else "soon"
    return create_notification(
        user=assignee,
        notification_type=NotificationType.DEADLINE_APPROACHING,
        title="Task deadline approaching",
        message=f"'{task.title}' is due on {due_display}.",
        actor=task.created_by,
        team=task.team,
        metadata={
            "task_id": str(task.id),
            "team_id": str(task.team_id),
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "reminder_window_hours": reminder_window_hours,
        },
        target_type="task",
        target_id=task.id,
    )
