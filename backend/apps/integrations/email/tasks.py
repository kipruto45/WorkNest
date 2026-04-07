from __future__ import annotations

from celery import shared_task
from django.conf import settings

from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, create_audit_log
from apps.integrations.email.base import QueuedEmailPayload
from apps.integrations.email.services import (
    deliver_prepared_email,
    mark_email_delivery_failed,
    mark_email_delivery_processing,
    mark_email_delivery_sent,
)
from apps.integrations.exceptions import EmailSendFailedError
from apps.integrations.models import EmailDelivery


@shared_task(bind=True, max_retries=5)
def deliver_email_task(self, delivery_id: str, payload_data: dict) -> bool:
    delivery = EmailDelivery.objects.filter(id=delivery_id).first()
    if delivery is None:
        return False

    payload = QueuedEmailPayload.from_dict(payload_data)
    mark_email_delivery_processing(delivery=delivery)

    try:
        provider_response = deliver_prepared_email(payload=payload)
    except EmailSendFailedError as exc:
        mark_email_delivery_failed(delivery=delivery, message=str(exc))
        create_audit_log(
            action=AuditAction.EMAIL_FAILED,
            target_type="email_delivery",
            target_id=str(delivery.id),
            target_repr=delivery.subject,
            metadata=build_audit_metadata(email_type=delivery.email_type, recipient_email=delivery.recipient_email),
        )
        configured_retries = int(getattr(settings, "EMAIL_TASK_MAX_RETRIES", 3))
        backoff_seconds = int(getattr(settings, "EMAIL_RETRY_BACKOFF_SECONDS", 2))
        if not getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) and self.request.retries < configured_retries:
            raise self.retry(exc=exc, countdown=backoff_seconds ** (self.request.retries + 1))
        return False
    except Exception as exc:  # pragma: no cover
        mark_email_delivery_failed(delivery=delivery, message="The email could not be rendered or delivered.")
        create_audit_log(
            action=AuditAction.EMAIL_FAILED,
            target_type="email_delivery",
            target_id=str(delivery.id),
            target_repr=delivery.subject,
            metadata=build_audit_metadata(email_type=delivery.email_type, recipient_email=delivery.recipient_email),
        )
        configured_retries = int(getattr(settings, "EMAIL_TASK_MAX_RETRIES", 3))
        backoff_seconds = int(getattr(settings, "EMAIL_RETRY_BACKOFF_SECONDS", 2))
        if not getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) and self.request.retries < configured_retries:
            raise self.retry(exc=exc, countdown=backoff_seconds ** (self.request.retries + 1))
        return False

    mark_email_delivery_sent(delivery=delivery, provider_response=provider_response)
    create_audit_log(
        action=AuditAction.EMAIL_SENT,
        target_type="email_delivery",
        target_id=str(delivery.id),
        target_repr=delivery.subject,
        metadata=build_audit_metadata(
            email_type=delivery.email_type,
            recipient_email=delivery.recipient_email,
            provider=provider_response.get("provider"),
        ),
    )
    return True
