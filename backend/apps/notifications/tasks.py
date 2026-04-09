from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from celery import shared_task

from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, create_audit_log
from apps.integrations.models import SMSDelivery
from apps.integrations.email.services import send_notification_email
from apps.integrations.sms.exceptions import SMSSendFailedError
from apps.integrations.sms.services import deliver_sms_message, mark_sms_delivery_failed, mark_sms_delivery_sending, mark_sms_delivery_sent
from apps.integrations.validators import sanitize_provider_error
from apps.notifications.constants import NotificationType
from apps.notifications.models import Notification
from apps.tasks.models import Task


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_notification_email_task(self, notification_id: str) -> bool:
    notification = (
        Notification.objects.select_related("user", "actor", "team")
        .filter(id=notification_id)
        .first()
    )
    if not notification or not notification.user.email:
        return False

    send_notification_email(notification=notification)
    return True


@shared_task(bind=True, max_retries=5)
def deliver_sms_task(self, delivery_id: str) -> bool:
    delivery = SMSDelivery.objects.filter(id=delivery_id).first()
    if delivery is None:
        return False

    mark_sms_delivery_sending(delivery=delivery)

    try:
        provider_response = deliver_sms_message(to=delivery.phone_number, message=delivery.message_body, metadata=delivery.metadata)
    except SMSSendFailedError as exc:
        error_message = sanitize_provider_error(exc, fallback_message="SMS delivery failed.")
        mark_sms_delivery_failed(delivery=delivery, message=error_message)
        create_audit_log(
            action=AuditAction.SMS_FAILED,
            target_type="sms_delivery",
            target_id=str(delivery.id),
            target_repr=delivery.phone_number,
            metadata=build_audit_metadata(message_type=delivery.message_type, phone_number=delivery.phone_number),
        )
        configured_retries = int(getattr(settings, "SMS_MAX_RETRIES", 3))
        backoff_seconds = int(getattr(settings, "SMS_RETRY_BACKOFF_SECONDS", 2))
        if not getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) and self.request.retries < configured_retries:
            raise self.retry(exc=exc, countdown=backoff_seconds ** (self.request.retries + 1))
        return False
    except Exception as exc:  # pragma: no cover
        mark_sms_delivery_failed(delivery=delivery, message="SMS delivery failed.")
        create_audit_log(
            action=AuditAction.SMS_FAILED,
            target_type="sms_delivery",
            target_id=str(delivery.id),
            target_repr=delivery.phone_number,
            metadata=build_audit_metadata(message_type=delivery.message_type, phone_number=delivery.phone_number),
        )
        configured_retries = int(getattr(settings, "SMS_MAX_RETRIES", 3))
        backoff_seconds = int(getattr(settings, "SMS_RETRY_BACKOFF_SECONDS", 2))
        if not getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) and self.request.retries < configured_retries:
            raise self.retry(exc=exc, countdown=backoff_seconds ** (self.request.retries + 1))
        return False

    mark_sms_delivery_sent(delivery=delivery, provider_response=provider_response)
    create_audit_log(
        action=AuditAction.SMS_SENT,
        target_type="sms_delivery",
        target_id=str(delivery.id),
        target_repr=delivery.phone_number,
        metadata=build_audit_metadata(
            message_type=delivery.message_type,
            phone_number=delivery.phone_number,
            provider=provider_response.get("provider"),
        ),
    )
    return True


@shared_task
def send_deadline_approaching_notifications_task() -> int:
    from apps.notifications.services import notify_deadline_approaching

    now = timezone.now()
    created_count = 0
    reminder_windows = [int(value) for value in getattr(settings, "NOTIFICATION_DEADLINE_REMINDER_WINDOWS_HOURS", [24])]
    grace_minutes = int(getattr(settings, "NOTIFICATION_DEADLINE_REMINDER_GRACE_MINUTES", 30))

    for reminder_hours in reminder_windows:
        window_start = now + timedelta(hours=reminder_hours) - timedelta(minutes=grace_minutes)
        window_end = now + timedelta(hours=reminder_hours) + timedelta(minutes=grace_minutes)

        tasks = (
            Task.objects.select_related("assigned_to", "team", "created_by")
            .filter(
                assigned_to__isnull=False,
                team__is_archived=False,
                is_archived=False,
                due_date__isnull=False,
                due_date__gte=window_start,
                due_date__lte=window_end,
            )
            .exclude(status=Task.Status.DONE)
        )

        for task in tasks:
            notification = notify_deadline_approaching(task=task, reminder_window_hours=reminder_hours)
            if notification is not None:
                created_count += 1
    return created_count
