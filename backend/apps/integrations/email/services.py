from __future__ import annotations

import logging
import threading
from types import SimpleNamespace
from typing import Any

from django.conf import settings
from django.db import connection
from django.db import transaction
from django.utils import timezone

from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, create_audit_log
from apps.integrations.constants import DEFAULT_EMAIL_PROVIDER, EMAIL_PROVIDER_SENDGRID, EMAIL_PROVIDER_SMTP
from apps.integrations.email.base import EmailMessagePayload, QueuedEmailPayload
from apps.integrations.email.builders import (
    build_admin_communication_email_payload,
    build_attachment_uploaded_email_payload,
    build_comment_posted_email_payload,
    build_credential_change_email_payload,
    build_deadline_approaching_email_payload,
    build_email_verification_email_payload,
    build_invitation_accepted_email_payload,
    build_invitation_reminder_email_payload,
    build_invitation_revoked_email_payload,
    build_mentioned_email_payload,
    build_notification_email_payload,
    build_password_reset_email_payload,
    build_role_changed_email_payload,
    build_task_assigned_email_payload,
    build_task_status_changed_email_payload,
    build_team_invite_email_payload,
    build_welcome_email_payload,
)
from apps.integrations.email.sendgrid import SendGridEmailProvider
from apps.integrations.email.smtp import SMTPEmailProvider
from apps.integrations.email.templates import render_email_template
from apps.integrations.exceptions import EmailDeliveryError, EmailSendFailedError, IntegrationConfigurationError
from apps.integrations.models import EmailDelivery
from apps.integrations.validators import validate_provider_name

logger = logging.getLogger(__name__)


def _build_invitation_like(*, team, recipient_email: str, role: str, token: str = "", invitation_link: str = "", expires_at=None, custom_message: str = "", invited_by=None, invitation_id: str = ""):
    from apps.memberships.models import Membership

    role_label = dict(Membership.Role.choices).get(role, role.replace("_", " ").title())

    class InvitationLike(SimpleNamespace):
        def get_role_display(self):
            return role_label

    resolved_token = token or invitation_link.rstrip("/").split("/")[-1]
    return InvitationLike(
        id=invitation_id or resolved_token or "ad-hoc",
        team=team,
        team_id=team.id,
        email=recipient_email,
        role=role,
        token=resolved_token,
        custom_message=custom_message,
        invited_by=invited_by,
        expires_at=expires_at,
        updated_at=timezone.now(),
    )


def get_email_provider(provider_name: str | None = None):
    resolved_provider = validate_provider_name(
        provider_name=provider_name or getattr(settings, "EMAIL_PROVIDER", DEFAULT_EMAIL_PROVIDER),
        supported_providers={EMAIL_PROVIDER_SMTP, EMAIL_PROVIDER_SENDGRID},
        provider_kind="email",
    )
    if resolved_provider == EMAIL_PROVIDER_SENDGRID:
        return SendGridEmailProvider()
    return SMTPEmailProvider()


def build_email_message_payload(*, payload: QueuedEmailPayload) -> EmailMessagePayload:
    rendered = render_email_template(template_name=payload.template_name, context=payload.context)
    return EmailMessagePayload(
        to=[payload.recipient_email],
        subject=payload.subject,
        text_body=rendered.text_body,
        html_body=rendered.html_body,
        from_email=payload.from_email,
        reply_to=payload.reply_to,
        headers=payload.headers,
        metadata=payload.metadata,
        provider_metadata=payload.provider_metadata,
    )


def send_system_email(*, payload: EmailMessagePayload, provider_name: str | None = None) -> dict[str, Any]:
    return get_email_provider(provider_name=provider_name).send_email(payload)


def deliver_prepared_email(*, payload: QueuedEmailPayload) -> dict[str, Any]:
    message_payload = build_email_message_payload(payload=payload)
    return send_system_email(payload=message_payload, provider_name=payload.provider_name)


def _should_skip_email(*, user=None, email_type: str) -> bool:
    if user is None:
        return False
    if not getattr(user, "is_active", True):
        return True

    preferences = getattr(user, "email_preferences", None) or getattr(user, "notification_preferences", None) or {}
    if isinstance(preferences, dict):
        channel_prefs = preferences.get("channels") or {}
        email_prefs = channel_prefs.get("email") or {}
        if email_type in email_prefs and isinstance(email_prefs[email_type], bool):
            return not bool(email_prefs[email_type])
    preference_map = getattr(
        settings,
        "EMAIL_TYPE_PREFERENCE_MAP",
        {
            "task_assigned": "task_assignment_emails",
            "deadline_approaching": "deadline_reminder_emails",
            "comment_posted": "comment_emails",
            "mentioned_in_comment": "mention_emails",
            "team_invite": "team_invite_emails",
        },
    )
    preference_key = preference_map.get(email_type)
    if preference_key and isinstance(preferences, dict) and preference_key in preferences:
        return not bool(preferences[preference_key])
    return False


def _create_delivery_record(*, payload: QueuedEmailPayload, status: str = EmailDelivery.Status.QUEUED, last_error: str = "") -> EmailDelivery:
    return EmailDelivery.objects.create(
        email_type=payload.email_type,
        template_name=payload.template_name,
        recipient_email=payload.recipient_email,
        subject=payload.subject,
        status=status,
        source=payload.source,
        dedupe_key=payload.dedupe_key,
        related_object_type=payload.related_object_type,
        related_object_id=payload.related_object_id,
        metadata=build_audit_metadata(**payload.metadata),
        last_error=last_error,
        last_attempt_at=timezone.now() if status in {EmailDelivery.Status.FAILED, EmailDelivery.Status.SKIPPED} else None,
    )


def _find_existing_delivery(*, dedupe_key: str) -> EmailDelivery | None:
    if not dedupe_key:
        return None
    return EmailDelivery.objects.filter(
        dedupe_key=dedupe_key,
        status__in=[EmailDelivery.Status.QUEUED, EmailDelivery.Status.PROCESSING, EmailDelivery.Status.SENT],
    ).first()


def _log_email_action(*, actor=None, action: str, payload: QueuedEmailPayload, delivery: EmailDelivery, metadata: dict[str, Any] | None = None) -> None:
    try:
        create_audit_log(
            actor=actor,
            action=action,
            target_type="email_delivery",
            target_id=str(delivery.id),
            target_repr=payload.subject,
            metadata=build_audit_metadata(
                email_type=payload.email_type,
                recipient_email=payload.recipient_email,
                template_name=payload.template_name,
                source=payload.source,
                related_object_type=payload.related_object_type,
                related_object_id=payload.related_object_id,
                **(metadata or {}),
            ),
        )
    except Exception:
        logger.exception(
            "email_audit_log_failed",
            extra={"delivery_id": str(delivery.id), "email_type": payload.email_type, "action": action},
        )


def _safe_record_delivery_event(*, action: str, delivery: EmailDelivery, metadata: dict[str, Any]) -> None:
    try:
        create_audit_log(
            action=action,
            target_type="email_delivery",
            target_id=str(delivery.id),
            target_repr=delivery.subject,
            metadata=metadata,
        )
    except Exception:
        logger.exception(
            "email_delivery_event_log_failed",
            extra={"delivery_id": str(delivery.id), "email_type": delivery.email_type, "action": action},
        )


def _is_async_email_delivery_enabled() -> bool:
    return str(getattr(settings, "EMAIL_DELIVERY_MODE", "sync")).strip().lower() == "async"


def _deliver_email_background(*, delivery_id: str, payload_data: dict[str, Any]) -> None:
    def runner() -> None:
        from django.db import close_old_connections

        close_old_connections()
        try:
            delivery = EmailDelivery.objects.filter(id=delivery_id).first()
            if delivery is None:
                return
            payload = QueuedEmailPayload.from_dict(payload_data)
            _deliver_email_inline(payload=payload, delivery=delivery)
        except Exception:  # pragma: no cover
            logger.exception("email_background_delivery_failed", extra={"delivery_id": delivery_id})
        finally:
            close_old_connections()

    threading.Thread(
        target=runner,
        name=f"email-delivery-{delivery_id}",
        daemon=True,
    ).start()


def _schedule_email_delivery(*, payload: QueuedEmailPayload, delivery: EmailDelivery) -> None:
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        _deliver_email_inline(payload=payload, delivery=delivery)
        return

    if _is_async_email_delivery_enabled():
        from apps.integrations.email.tasks import deliver_email_task

        try:
            async_result = deliver_email_task.delay(str(delivery.id), payload.to_dict())
            EmailDelivery.objects.filter(id=delivery.id).update(celery_task_id=str(async_result.id or ""))
            return
        except Exception:  # pragma: no cover
            logger.exception("email_queue_failed", extra={"delivery_id": str(delivery.id), "email_type": payload.email_type})
            _deliver_email_inline(payload=payload, delivery=delivery)
            return

    _deliver_email_background(delivery_id=str(delivery.id), payload_data=payload.to_dict())


def _deliver_email_inline(*, payload: QueuedEmailPayload, delivery: EmailDelivery) -> EmailDelivery:
    mark_email_delivery_processing(delivery=delivery)

    try:
        provider_response = deliver_prepared_email(payload=payload)
    except (EmailDeliveryError, IntegrationConfigurationError) as exc:
        mark_email_delivery_failed(delivery=delivery, message=str(exc))
        _safe_record_delivery_event(
            action=AuditAction.EMAIL_FAILED,
            metadata=build_audit_metadata(email_type=delivery.email_type, recipient_email=delivery.recipient_email),
            delivery=delivery,
        )
        return delivery
    except Exception:  # pragma: no cover
        mark_email_delivery_failed(delivery=delivery, message="The email could not be rendered or delivered.")
        _safe_record_delivery_event(
            action=AuditAction.EMAIL_FAILED,
            metadata=build_audit_metadata(email_type=delivery.email_type, recipient_email=delivery.recipient_email),
            delivery=delivery,
        )
        logger.exception("email_inline_delivery_failed", extra={"delivery_id": str(delivery.id), "email_type": payload.email_type})
        return delivery

    mark_email_delivery_sent(delivery=delivery, provider_response=provider_response)
    _safe_record_delivery_event(
        action=AuditAction.EMAIL_SENT,
        metadata=build_audit_metadata(
            email_type=delivery.email_type,
            recipient_email=delivery.recipient_email,
            provider=provider_response.get("provider"),
        ),
        delivery=delivery,
    )
    return delivery


def queue_email(*, payload: QueuedEmailPayload, actor=None, user=None) -> EmailDelivery:
    existing = _find_existing_delivery(dedupe_key=payload.dedupe_key)
    if existing is not None:
        return existing

    if _should_skip_email(user=user, email_type=payload.email_type):
        delivery = _create_delivery_record(
            payload=payload,
            status=EmailDelivery.Status.SKIPPED,
            last_error="Skipped because email preferences disabled this notification.",
        )
        _log_email_action(actor=actor, action=AuditAction.EMAIL_SKIPPED, payload=payload, delivery=delivery)
        return delivery

    delivery = _create_delivery_record(payload=payload)

    def on_commit() -> None:
        _schedule_email_delivery(payload=payload, delivery=delivery)

    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) or not connection.in_atomic_block:
        on_commit()
    else:
        transaction.on_commit(on_commit)
    _log_email_action(actor=actor, action=AuditAction.EMAIL_QUEUED, payload=payload, delivery=delivery)
    return delivery


def mark_email_delivery_processing(*, delivery: EmailDelivery) -> EmailDelivery:
    delivery.status = EmailDelivery.Status.PROCESSING
    delivery.attempt_count += 1
    delivery.last_attempt_at = timezone.now()
    delivery.last_error = ""
    delivery.save(update_fields=["status", "attempt_count", "last_attempt_at", "last_error", "updated_at"])
    return delivery


def mark_email_delivery_sent(*, delivery: EmailDelivery, provider_response: dict[str, Any]) -> EmailDelivery:
    delivery.status = EmailDelivery.Status.SENT
    delivery.provider = str(provider_response.get("provider", ""))[:32]
    delivery.provider_response = provider_response
    delivery.provider_message_id = str(provider_response.get("message_id", ""))[:255]
    delivery.sent_at = timezone.now()
    delivery.last_error = ""
    delivery.save(
        update_fields=[
            "status",
            "provider",
            "provider_response",
            "provider_message_id",
            "sent_at",
            "last_error",
            "updated_at",
        ]
    )
    return delivery


def mark_email_delivery_failed(*, delivery: EmailDelivery, message: str) -> EmailDelivery:
    delivery.status = EmailDelivery.Status.FAILED
    delivery.last_error = str(message)[:2000]
    delivery.last_attempt_at = timezone.now()
    delivery.save(update_fields=["status", "last_error", "last_attempt_at", "updated_at"])
    return delivery


def send_password_reset_email(*, user, reset_url: str, expires_in_minutes: int = 30) -> dict[str, Any]:
    return deliver_prepared_email(
        payload=build_password_reset_email_payload(user=user, reset_url=reset_url, expires_in_minutes=expires_in_minutes)
    )


def queue_password_reset_email(*, user, reset_url: str, actor=None, expires_in_minutes: int = 30) -> EmailDelivery:
    return queue_email(
        payload=build_password_reset_email_payload(user=user, reset_url=reset_url, expires_in_minutes=expires_in_minutes),
        actor=actor or user,
        user=user,
    )


def queue_email_verification_email(*, user, verification_url: str, actor=None) -> EmailDelivery:
    return queue_email(
        payload=build_email_verification_email_payload(user=user, verification_url=verification_url),
        actor=actor or user,
        user=user,
    )


def queue_credential_change_email(*, user, new_email: str, code: str, actor=None) -> EmailDelivery:
    return queue_email(
        payload=build_credential_change_email_payload(user=user, new_email=new_email, code=code),
        actor=actor or user,
        user=user,
    )


def send_team_invite_email(*, invitation=None, team=None, recipient_email: str = "", role: str = "", invitation_link: str = "", expires_at=None, custom_message: str = "", invited_by=None) -> dict[str, Any]:
    invitation = invitation or _build_invitation_like(
        team=team,
        recipient_email=recipient_email,
        role=role,
        invitation_link=invitation_link,
        expires_at=expires_at,
        custom_message=custom_message,
        invited_by=invited_by,
    )
    return deliver_prepared_email(payload=build_team_invite_email_payload(invitation=invitation))


def queue_team_invite_email(*, invitation, actor=None) -> EmailDelivery:
    return queue_email(payload=build_team_invite_email_payload(invitation=invitation), actor=actor or invitation.invited_by)


def send_invitation_reminder_email(*, invitation=None, team=None, recipient_email: str = "", role: str = "", invitation_link: str = "", expires_at=None, custom_message: str = "", invited_by=None) -> dict[str, Any]:
    invitation = invitation or _build_invitation_like(
        team=team,
        recipient_email=recipient_email,
        role=role,
        invitation_link=invitation_link,
        expires_at=expires_at,
        custom_message=custom_message,
        invited_by=invited_by,
    )
    return deliver_prepared_email(payload=build_invitation_reminder_email_payload(invitation=invitation))


def queue_invitation_reminder_email(*, invitation, actor=None) -> EmailDelivery:
    return queue_email(payload=build_invitation_reminder_email_payload(invitation=invitation), actor=actor or invitation.invited_by)


def send_invitation_revoked_email(*, invitation=None, team=None, recipient_email: str = "", invited_by=None, actor=None) -> dict[str, Any]:
    invitation = invitation or _build_invitation_like(
        team=team,
        recipient_email=recipient_email,
        role="member",
        invited_by=invited_by,
    )
    return deliver_prepared_email(payload=build_invitation_revoked_email_payload(invitation=invitation, actor=actor))


def queue_invitation_revoked_email(*, invitation, actor=None) -> EmailDelivery:
    return queue_email(payload=build_invitation_revoked_email_payload(invitation=invitation, actor=actor), actor=actor or invitation.invited_by)


def send_notification_email(*, notification) -> dict[str, Any]:
    return deliver_prepared_email(payload=build_notification_email_payload(notification=notification))


def queue_notification_email(*, notification) -> EmailDelivery:
    return queue_email(
        payload=build_notification_email_payload(notification=notification),
        actor=notification.actor,
        user=notification.user,
    )


def queue_admin_communication_email(*, communication, recipient, actor=None) -> EmailDelivery:
    return queue_email(
        payload=build_admin_communication_email_payload(communication=communication, recipient=recipient, actor=actor),
        actor=actor,
        user=recipient,
    )


def send_welcome_email(*, user, dashboard_url: str | None = None) -> dict[str, Any]:
    return deliver_prepared_email(payload=build_welcome_email_payload(user=user, dashboard_url=dashboard_url))


def queue_welcome_email(*, user, actor=None, dashboard_url: str | None = None) -> EmailDelivery:
    return queue_email(payload=build_welcome_email_payload(user=user, dashboard_url=dashboard_url), actor=actor or user, user=user)


def send_task_assigned_email(*, task, assigner, assignee) -> dict[str, Any]:
    return deliver_prepared_email(payload=build_task_assigned_email_payload(task=task, assigner=assigner, assignee=assignee))


def queue_task_assigned_email(*, task, assigner, assignee) -> EmailDelivery:
    return queue_email(payload=build_task_assigned_email_payload(task=task, assigner=assigner, assignee=assignee), actor=assigner, user=assignee)


def send_deadline_approaching_email(*, task, recipient=None, reminder_window_hours: int = 24) -> dict[str, Any]:
    return deliver_prepared_email(
        payload=build_deadline_approaching_email_payload(
            task=task,
            recipient=recipient or task.assigned_to,
            reminder_window_hours=reminder_window_hours,
        )
    )


def queue_deadline_approaching_email(*, task, recipient=None, reminder_window_hours: int = 24, actor=None) -> EmailDelivery:
    resolved_recipient = recipient or task.assigned_to
    return queue_email(
        payload=build_deadline_approaching_email_payload(
            task=task,
            recipient=resolved_recipient,
            reminder_window_hours=reminder_window_hours,
        ),
        actor=actor or task.created_by,
        user=resolved_recipient,
    )


def send_comment_posted_email(*, comment, task, recipient) -> dict[str, Any]:
    return deliver_prepared_email(payload=build_comment_posted_email_payload(comment=comment, task=task, recipient=recipient))


def queue_comment_posted_email(*, comment, task, recipient, actor=None) -> EmailDelivery:
    return queue_email(
        payload=build_comment_posted_email_payload(comment=comment, task=task, recipient=recipient),
        actor=actor or comment.author,
        user=recipient,
    )


def send_mentioned_email(*, comment, task, mentioned_user) -> dict[str, Any]:
    return deliver_prepared_email(payload=build_mentioned_email_payload(comment=comment, task=task, mentioned_user=mentioned_user))


def queue_mentioned_email(*, comment, task, mentioned_user, actor=None) -> EmailDelivery:
    return queue_email(
        payload=build_mentioned_email_payload(comment=comment, task=task, mentioned_user=mentioned_user),
        actor=actor or comment.author,
        user=mentioned_user,
    )


def queue_invitation_accepted_email(*, invitation, recipient_user, actor) -> EmailDelivery:
    return queue_email(
        payload=build_invitation_accepted_email_payload(invitation=invitation, recipient_user=recipient_user, actor=actor),
        actor=actor,
        user=recipient_user,
    )


def queue_role_changed_email(*, membership, actor, old_role: str, new_role: str) -> EmailDelivery:
    return queue_email(
        payload=build_role_changed_email_payload(membership=membership, actor=actor, old_role=old_role, new_role=new_role),
        actor=actor,
        user=membership.user,
    )


def queue_task_status_changed_email(*, task, previous_status: str, changed_by, recipient) -> EmailDelivery:
    return queue_email(
        payload=build_task_status_changed_email_payload(task=task, previous_status=previous_status, changed_by=changed_by, recipient=recipient),
        actor=changed_by,
        user=recipient,
    )


def queue_attachment_uploaded_email(*, attachment, recipient, actor=None) -> EmailDelivery:
    return queue_email(
        payload=build_attachment_uploaded_email_payload(attachment=attachment, recipient=recipient),
        actor=actor or attachment.uploaded_by,
        user=recipient,
    )
