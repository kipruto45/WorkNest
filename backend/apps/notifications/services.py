from __future__ import annotations

import logging

from django.conf import settings
from django.db import connection
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, log_notification_action
from apps.integrations.email.builders import _get_frontend_url
from apps.integrations.sms.services import queue_sms, sanitize_sms_message
from apps.notifications.constants import (
    NOTIFICATION_CREATED_EVENT,
    NOTIFICATION_DELETED_EVENT,
    NOTIFICATION_UNREAD_COUNT_EVENT,
    NOTIFICATION_UPDATED_EVENT,
    NotificationType,
)
from apps.notifications.models import AdminCommunication, AdminCommunicationRecipient, Notification
from apps.realtime.services import (
    send_notification_deleted_event,
    send_notification_event,
    send_team_invite_event,
    send_unread_count_event,
    send_user_event,
)

logger = logging.getLogger(__name__)


def _build_frontend_task_link(*, task) -> str:
    base = _get_frontend_url().rstrip("/")
    return f"{base}/tasks/{task.id}" if base else f"/tasks/{task.id}"


def _build_frontend_invitation_link(*, invitation) -> str:
    base = _get_frontend_url().rstrip("/")
    return f"{base}/invitations/{invitation.token}" if base else f"/invitations/{invitation.token}"


def _format_due_display(value) -> str:
    if not value:
        return "soon"
    return timezone.localtime(value).strftime("%b %d, %H:%M")


def send_task_assigned_sms(*, task, recipient, actor=None):
    return queue_sms(
        user=recipient,
        phone_number=recipient.phone_number or "",
        message_type=NotificationType.TASK_ASSIGNED,
        message_body=sanitize_sms_message(
            f"You have been assigned: {task.title}. Due: {_format_due_display(task.due_date)}. Open app: {_build_frontend_task_link(task=task)}"
        ),
        metadata={"task_id": str(task.id), "team_id": str(task.team_id), "actor_id": str(getattr(actor, 'id', ''))},
        related_object_type="task",
        related_object_id=str(task.id),
        dedupe_key=f"sms:task-assigned:{task.id}:{recipient.id}:{task.updated_at.isoformat()}",
        actor=actor,
        source="notifications.task_assignment",
    )


def send_deadline_reminder_sms(*, task, recipient, reminder_window_hours: int = 24):
    return queue_sms(
        user=recipient,
        phone_number=recipient.phone_number or "",
        message_type=NotificationType.DEADLINE_APPROACHING,
        message_body=sanitize_sms_message(
            f"Reminder: {task.title} is due {_format_due_display(task.due_date)}. Check it now: {_build_frontend_task_link(task=task)}"
        ),
        metadata={"task_id": str(task.id), "reminder_window_hours": reminder_window_hours},
        related_object_type="task",
        related_object_id=str(task.id),
        dedupe_key=f"sms:deadline:{task.id}:{recipient.id}:{reminder_window_hours}",
        actor=task.created_by,
        source="notifications.deadline",
    )


def send_mention_sms(*, comment, recipient):
    return queue_sms(
        user=recipient,
        phone_number=recipient.phone_number or "",
        message_type=NotificationType.MENTIONED_IN_COMMENT,
        message_body=sanitize_sms_message(
            f"{comment.author.name if comment.author else 'A teammate'} mentioned you in {comment.task.title}. Open app: {_build_frontend_task_link(task=comment.task)}"
        ),
        metadata={"task_id": str(comment.task_id), "comment_id": str(comment.id)},
        related_object_type="comment",
        related_object_id=str(comment.id),
        dedupe_key=f"sms:mention:{comment.id}:{recipient.id}",
        actor=comment.author,
        source="notifications.mentions",
    )


def send_invite_sms(*, invitation, recipient):
    return queue_sms(
        user=recipient,
        phone_number=recipient.phone_number or "",
        message_type=NotificationType.TEAM_INVITE,
        message_body=sanitize_sms_message(
            f"You have been invited to join {invitation.team.name}. Accept here: {_build_frontend_invitation_link(invitation=invitation)}"
        ),
        metadata={"team_id": str(invitation.team_id), "invitation_id": str(invitation.id)},
        related_object_type="team_invitation",
        related_object_id=str(invitation.id),
        dedupe_key=f"sms:invite:{invitation.id}:{recipient.id}",
        actor=invitation.invited_by,
        source="notifications.invites",
    )


def send_admin_broadcast_sms(*, communication, recipient, actor=None):
    preview = sanitize_sms_message(f"{getattr(settings, 'APP_NAME', 'WorkNest')}: {communication.message}", limit=280)
    return queue_sms(
        user=recipient,
        phone_number=recipient.phone_number or "",
        message_type="admin_broadcast",
        message_body=preview,
        metadata={"communication_id": str(communication.id), "channel_type": communication.channel_type},
        related_object_type="admin_communication",
        related_object_id=str(communication.id),
        dedupe_key=f"sms:admin-broadcast:{communication.id}:{recipient.id}",
        actor=actor,
        source="notifications.admin_communication",
    )


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


def resolve_notification_preferences(*, user, notification_type: str) -> dict:
    preferences = getattr(user, "notification_preferences", {}) or {}
    channel_prefs = preferences.get("channels") or {}
    in_app_prefs = channel_prefs.get("in_app") or {}
    email_prefs = channel_prefs.get("email") or {}

    legacy_map = {
        NotificationType.TASK_ASSIGNED: "task_assignment_emails",
        NotificationType.DEADLINE_APPROACHING: "deadline_reminder_emails",
        NotificationType.COMMENT_POSTED: "comment_emails",
        NotificationType.MENTIONED_IN_COMMENT: "mention_emails",
        NotificationType.TEAM_INVITE: "team_invite_emails",
        NotificationType.ADMIN_MESSAGE: "admin_message_emails",
    }
    legacy_key = legacy_map.get(notification_type)

    in_app_enabled = in_app_prefs.get(notification_type, True)
    email_enabled = email_prefs.get(notification_type, True)

    if legacy_key and legacy_key in preferences:
        email_enabled = bool(preferences.get(legacy_key))

    return {"in_app": bool(in_app_enabled), "email": bool(email_enabled)}


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
    preferences = resolve_notification_preferences(user=user, notification_type=notification_type)
    in_app_allowed = preferences["in_app"]
    email_allowed = preferences["email"]
    if send_email is True:
        email_allowed = True
    elif send_email is False:
        email_allowed = False

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
        is_muted=not in_app_allowed,
    )

    def on_commit() -> None:
        if not notification.is_muted:
            send_notification_event(notification=notification, event_name=NOTIFICATION_CREATED_EVENT)
            send_unread_count_event(user=notification.user)
        if email_allowed and should_send_email_for_type(notification_type=notification.type):
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
        preferences = resolve_notification_preferences(user=user, notification_type=notification_type)
        in_app_allowed = preferences["in_app"]
        email_allowed = preferences["email"]
        if send_email is True:
            email_allowed = True
        elif send_email is False:
            email_allowed = False
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
                is_muted=not in_app_allowed,
            )
        )
    created = Notification.objects.bulk_create(notifications)

    def on_commit() -> None:
        for notification in created:
            if not notification.is_muted:
                send_notification_event(notification=notification, event_name=NOTIFICATION_CREATED_EVENT)
                send_unread_count_event(user=notification.user)
            if (send_email is True or send_email is None) and should_send_email_for_type(notification_type=notification.type):
                preferences = resolve_notification_preferences(user=notification.user, notification_type=notification.type)
                if send_email is True or preferences["email"]:
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


def _resolve_admin_communication_recipients(*, audience_type: str, user_ids: list[str], team_ids: list[str], actor) -> list[dict]:
    from apps.memberships.models import Membership
    from apps.teams.models import Team
    from apps.users.models import User

    resolved_user_ids = [str(user_id) for user_id in user_ids]
    resolved_team_ids = [str(team_id) for team_id in team_ids]

    recipients: dict[str, dict] = {}

    if audience_type == AdminCommunication.AudienceType.ALL_USERS:
        queryset = User.objects.filter(is_active=True, is_staff=False).exclude(id=getattr(actor, "id", None))
        for user in queryset.order_by("name", "email"):
            recipients[str(user.id)] = {"user": user, "team": None}
        return list(recipients.values())

    if audience_type in {AdminCommunication.AudienceType.SINGLE_USER, AdminCommunication.AudienceType.SELECTED_USERS}:
        queryset = User.objects.filter(is_active=True, id__in=resolved_user_ids)
        for user in queryset:
            if getattr(actor, "id", None) and user.id == actor.id:
                continue
            recipients[str(user.id)] = {"user": user, "team": None}
        return list(recipients.values())

    if audience_type in {AdminCommunication.AudienceType.SINGLE_TEAM, AdminCommunication.AudienceType.SELECTED_TEAMS}:
        teams = list(Team.objects.filter(id__in=resolved_team_ids))
        if not teams:
            return []
        memberships = (
            Membership.objects.filter(team_id__in=[team.id for team in teams], status=Membership.Status.ACTIVE)
            .select_related("user", "team")
            .order_by("user__name", "user__email")
        )
        for membership in memberships:
            user = membership.user
            if not user.is_active or (getattr(actor, "id", None) and user.id == actor.id):
                continue
            recipients.setdefault(str(user.id), {"user": user, "team": membership.team})
        return list(recipients.values())

    return []


@transaction.atomic
def create_admin_communication(
    *,
    actor,
    audience_type: str,
    channel_type: str,
    title: str,
    message: str,
    user_ids: list[str] | None = None,
    team_ids: list[str] | None = None,
    scheduled_for=None,
    cta_label: str = "",
    cta_link: str = "",
    confirm_broadcast: bool = False,
) -> dict:
    resolved_user_ids = [str(user_id) for user_id in (user_ids or [])]
    resolved_team_ids = [str(team_id) for team_id in (team_ids or [])]
    communication = AdminCommunication.objects.create(
        title=title.strip(),
        message=message.strip(),
        audience_type=audience_type,
        channel_type=channel_type,
        created_by=actor,
        scheduled_for=scheduled_for,
        status=AdminCommunication.Status.SENT,
        cta_label=cta_label.strip(),
        cta_link=cta_link.strip(),
        audience_metadata={
            "user_ids": resolved_user_ids,
            "team_ids": resolved_team_ids,
        },
    )
    if channel_type in {
        AdminCommunication.ChannelType.SMS,
        AdminCommunication.ChannelType.SMS_AND_IN_APP,
        AdminCommunication.ChannelType.EMAIL_AND_SMS,
        AdminCommunication.ChannelType.ALL,
    }:
        log_notification_action(
            actor=actor,
            action=AuditAction.ADMIN_SMS_BROADCAST_CREATED,
            metadata=build_audit_metadata(title=communication.title, audience_type=audience_type, channel_type=channel_type),
            target_repr=communication.title,
            target_type="admin_communication",
        )

    if scheduled_for and scheduled_for > timezone.now():
        communication.status = AdminCommunication.Status.SCHEDULED
        communication.save(update_fields=["status", "updated_at"])
        return {
            "communication": communication,
            "recipient_count": 0,
            "delivered_in_app": 0,
            "delivered_email": 0,
        }

    recipients = _resolve_admin_communication_recipients(
        audience_type=audience_type,
        user_ids=resolved_user_ids,
        team_ids=resolved_team_ids,
        actor=actor,
    )
    if not recipients:
        communication.status = AdminCommunication.Status.FAILED
        communication.save(update_fields=["status", "updated_at"])
        raise ValidationError({"audience_type": ["No eligible recipients matched this selection."]})

    deliver_in_app = channel_type in {
        AdminCommunication.ChannelType.IN_APP,
        AdminCommunication.ChannelType.EMAIL_AND_IN_APP,
        AdminCommunication.ChannelType.SMS_AND_IN_APP,
        AdminCommunication.ChannelType.ALL,
    }
    deliver_email = channel_type in {
        AdminCommunication.ChannelType.EMAIL,
        AdminCommunication.ChannelType.EMAIL_AND_IN_APP,
        AdminCommunication.ChannelType.EMAIL_AND_SMS,
        AdminCommunication.ChannelType.ALL,
    }
    deliver_sms = channel_type in {
        AdminCommunication.ChannelType.SMS,
        AdminCommunication.ChannelType.SMS_AND_IN_APP,
        AdminCommunication.ChannelType.EMAIL_AND_SMS,
        AdminCommunication.ChannelType.ALL,
    }

    if deliver_sms and getattr(settings, "SMS_BROADCAST_CONFIRMATION_REQUIRED", True) and len(recipients) > 1 and not confirm_broadcast:
        raise ValidationError({"confirm_broadcast": ["Confirm this SMS broadcast before sending."]})

    in_app_notifications = []
    if deliver_in_app:
        notification_metadata = {
            "communication_id": str(communication.id),
            "audience_type": audience_type,
            "channel_type": channel_type,
            "cta_label": communication.cta_label,
            "cta_link": communication.cta_link,
        }
        in_app_notifications = create_bulk_notifications(
            users=[entry["user"] for entry in recipients],
            notification_type=NotificationType.ADMIN_MESSAGE,
            title=communication.title,
            message_builder=communication.message,
            actor=actor,
            metadata_builder=notification_metadata,
            target_type="admin_communication",
            target_id=communication.id,
            send_email=False,
        )

    email_deliveries = []
    if deliver_email:
        from apps.integrations.email.services import queue_admin_communication_email

        for entry in recipients:
            delivery = queue_admin_communication_email(
                communication=communication,
                recipient=entry["user"],
                actor=actor,
            )
            email_deliveries.append((entry["user"], delivery))

    sms_deliveries = []
    if deliver_sms:
        for entry in recipients:
            delivery = send_admin_broadcast_sms(communication=communication, recipient=entry["user"], actor=actor)
            sms_deliveries.append((entry["user"], delivery))

    recipient_records: list[AdminCommunicationRecipient] = []
    for entry in recipients:
        user = entry["user"]
        team = entry.get("team")
        email_delivery = None
        sms_delivery = None
        if deliver_email:
            match = next((delivery for delivery in email_deliveries if delivery[0].id == user.id), None)
            email_delivery = match[1] if match else None
        if deliver_sms:
            sms_match = next((delivery for delivery in sms_deliveries if delivery[0].id == user.id), None)
            sms_delivery = sms_match[1] if sms_match else None
        recipient_records.append(
            AdminCommunicationRecipient(
                communication=communication,
                user=user,
                team=team,
                channel_type=channel_type,
                in_app_sent=deliver_in_app,
                email_sent=deliver_email and email_delivery is not None,
                sms_sent=deliver_sms and sms_delivery is not None and sms_delivery.status != sms_delivery.Status.SKIPPED,
                email_delivery=email_delivery,
                sms_delivery=sms_delivery,
            )
        )
    AdminCommunicationRecipient.objects.bulk_create(recipient_records)

    communication.recipient_count = len(recipients)
    communication.delivered_in_app_count = len(in_app_notifications) if deliver_in_app else 0
    communication.delivered_email_count = len(email_deliveries) if deliver_email else 0
    communication.delivered_sms_count = sum(
        1 for _user, delivery in sms_deliveries if delivery.status in {delivery.Status.QUEUED, delivery.Status.SENDING, delivery.Status.SENT, delivery.Status.DELIVERED}
    )
    communication.failed_sms_count = sum(1 for _user, delivery in sms_deliveries if delivery.status in {delivery.Status.FAILED, delivery.Status.SKIPPED})
    communication.sent_at = timezone.now()
    if deliver_sms and communication.failed_sms_count and not communication.delivered_sms_count and not deliver_in_app and not deliver_email:
        communication.status = AdminCommunication.Status.FAILED
    elif deliver_sms and communication.failed_sms_count:
        communication.status = AdminCommunication.Status.PARTIAL_FAILURE
    else:
        communication.status = AdminCommunication.Status.SENT
    communication.save(
        update_fields=[
            "recipient_count",
            "delivered_in_app_count",
            "delivered_email_count",
            "delivered_sms_count",
            "failed_sms_count",
            "sent_at",
            "status",
            "updated_at",
        ]
    )

    log_notification_action(
        actor=actor,
        action=AuditAction.ADMIN_NOTIFICATION_SENT,
        metadata=build_audit_metadata(
            title=communication.title,
            audience_type=audience_type,
            channel_type=channel_type,
            recipient_count=communication.recipient_count,
            delivered_sms_count=communication.delivered_sms_count,
            failed_sms_count=communication.failed_sms_count,
        ),
        target_repr=communication.title,
        target_type="admin_communication",
    )

    if deliver_sms:
        log_notification_action(
            actor=actor,
            action=AuditAction.ADMIN_SMS_BROADCAST_SENT,
            metadata=build_audit_metadata(
                title=communication.title,
                recipient_count=communication.recipient_count,
                delivered_sms_count=communication.delivered_sms_count,
                failed_sms_count=communication.failed_sms_count,
            ),
            target_repr=communication.title,
            target_type="admin_communication",
        )

    return {
        "communication": communication,
        "recipient_count": communication.recipient_count,
        "delivered_in_app": communication.delivered_in_app_count,
        "delivered_email": communication.delivered_email_count,
        "delivered_sms": communication.delivered_sms_count,
        "failed_sms": communication.failed_sms_count,
    }


def notify_task_assignment(*, task, actor) -> Notification | None:
    assignee = task.assigned_to
    if assignee is None or (actor and assignee.id == actor.id):
        return None
    notification = create_notification(
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
    transaction.on_commit(lambda: send_task_assigned_sms(task=task, recipient=assignee, actor=actor))
    return notification


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
    transaction.on_commit(
        lambda: (
            send_team_invite_event(invitation=invitation, recipient_user=recipient_user),
            send_invite_sms(invitation=invitation, recipient=recipient_user),
        )
    )
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
    mentions = [user for user in (mentions or []) if user and user.id != comment.author_id]
    mentioned_ids = {user.id for user in mentions}

    mention_notifications: list[Notification] = []
    for user in mentions:
        notification = create_notification(
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
        mention_notifications.append(notification)
        transaction.on_commit(lambda user=user: send_mention_sms(comment=comment, recipient=user))

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

    return mention_notifications + participant_notifications


def notify_comment_mentions(*, comment, mentions: list | None = None) -> list[Notification]:
    mentions = [user for user in (mentions or []) if user and user.id != comment.author_id]
    notifications: list[Notification] = []
    for user in mentions:
        notification = create_notification(
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
        notifications.append(notification)
        transaction.on_commit(lambda user=user: send_mention_sms(comment=comment, recipient=user))
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
    notification = create_notification(
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
    transaction.on_commit(lambda: send_deadline_reminder_sms(task=task, recipient=assignee, reminder_window_hours=reminder_window_hours))
    return notification
