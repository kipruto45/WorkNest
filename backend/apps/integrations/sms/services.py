from __future__ import annotations

import logging
import random
import re
from typing import Any

from django.conf import settings
from django.db import connection, transaction
from django.utils import timezone

from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, create_audit_log
from apps.integrations.constants import DEFAULT_SMS_PROVIDER, SMS_PROVIDER_AFRICAS_TALKING, SUPPORTED_SMS_PROVIDERS
from apps.integrations.models import SMSDelivery
from apps.integrations.sms.africastalking import AfricasTalkingSMSProvider
from apps.integrations.sms.exceptions import SMSConfigurationError, SMSSendFailedError
from apps.integrations.validators import sanitize_provider_error, validate_provider_name

logger = logging.getLogger(__name__)

SMS_PREFERENCE_DEFAULTS = {
    "task_assignment_sms": True,
    "deadline_reminder_sms": True,
    "mention_sms": True,
    "invite_sms": True,
    "broadcast_sms": True,
}

SMS_MESSAGE_TYPE_PREFERENCE_MAP = {
    "task_assigned": "task_assignment_sms",
    "deadline_approaching": "deadline_reminder_sms",
    "mentioned_in_comment": "mention_sms",
    "team_invite": "invite_sms",
    "admin_broadcast": "broadcast_sms",
    "phone_verification": None,
}

SMS_MESSAGE_TYPE_ALIASES = {
    "admin_broadcast": {"admin_broadcast", "admin_message"},
}


def get_sms_provider(provider_name: str | None = None):
    resolved_provider = validate_provider_name(
        provider_name=provider_name or getattr(settings, "SMS_PROVIDER", DEFAULT_SMS_PROVIDER),
        supported_providers=SUPPORTED_SMS_PROVIDERS,
        provider_kind="sms",
    )
    if resolved_provider == SMS_PROVIDER_AFRICAS_TALKING:
        return AfricasTalkingSMSProvider()
    raise SMSConfigurationError("Unsupported SMS provider.")


def default_sms_preferences() -> dict[str, bool]:
    return dict(SMS_PREFERENCE_DEFAULTS)


def normalize_phone_number(phone_number: str, country_code: str | None = None) -> str:
    raw_value = str(phone_number or "").strip()
    if not raw_value:
        raise ValueError("Phone number is required.")

    digits = re.sub(r"[^\d+]", "", raw_value)
    if digits.count("+") > 1 or ("+" in digits and not digits.startswith("+")):
        raise ValueError("Enter a valid phone number.")

    default_country_code = str(country_code or getattr(settings, "DEFAULT_COUNTRY_CODE", "+254")).strip() or "+254"
    if not default_country_code.startswith("+"):
        default_country_code = f"+{default_country_code}"
    default_digits = re.sub(r"\D", "", default_country_code)

    if digits.startswith("+"):
        normalized_digits = re.sub(r"\D", "", digits)
    elif digits.startswith("00"):
        normalized_digits = re.sub(r"\D", "", digits[2:])
    elif digits.startswith("0"):
        normalized_digits = f"{default_digits}{re.sub(r'\\D', '', digits[1:])}"
    else:
        normalized_digits = re.sub(r"\D", "", digits)
        if default_digits and not normalized_digits.startswith(default_digits):
            normalized_digits = f"{default_digits}{normalized_digits}"

    if len(normalized_digits) < 9 or len(normalized_digits) > 15:
        raise ValueError("Enter a valid phone number.")
    if normalized_digits.startswith("0"):
        raise ValueError("Enter a valid phone number.")
    return f"+{normalized_digits}"


def validate_phone_number(phone_number: str, country_code: str | None = None) -> str:
    return normalize_phone_number(phone_number=phone_number, country_code=country_code)


def infer_phone_country_code(phone_number: str) -> str:
    normalized = normalize_phone_number(phone_number)
    if normalized.startswith("+254"):
        return "+254"
    if normalized.startswith("+1"):
        return "+1"
    digits = re.sub(r"\D", "", normalized)
    return f"+{digits[:3]}" if len(digits) >= 3 else str(getattr(settings, "DEFAULT_COUNTRY_CODE", "+254"))


def sanitize_sms_message(message: str, *, limit: int = 320) -> str:
    normalized = " ".join(str(message or "").split())
    return normalized[:limit].strip()


def generate_phone_verification_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def should_send_sms_for_user(*, user, message_type: str, force: bool = False) -> tuple[bool, str]:
    if force:
        return True, ""

    if not getattr(settings, "SMS_ENABLED", False) or not getattr(settings, "NOTIFICATION_SMS_ENABLED", True):
        return False, "SMS delivery is disabled."
    if not user or not getattr(user, "is_active", True):
        return False, "Recipient is inactive."
    if not getattr(user, "sms_opt_in", False):
        return False, "Recipient opted out of SMS notifications."
    if not getattr(user, "phone_number", ""):
        return False, "Recipient does not have a phone number configured."
    if getattr(settings, "SMS_REQUIRE_VERIFIED_PHONE", False) and not getattr(user, "phone_verified", False):
        return False, "Recipient phone number is not verified."

    preferences = default_sms_preferences()
    preferences.update(getattr(user, "sms_preferences", {}) or {})
    preference_key = SMS_MESSAGE_TYPE_PREFERENCE_MAP.get(message_type)
    if preference_key and not bool(preferences.get(preference_key, True)):
        return False, "Recipient disabled this SMS notification type."

    allowed_types = {str(value).strip().lower() for value in getattr(settings, "NOTIFICATION_SMS_TYPES", []) if str(value).strip()}
    message_type_aliases = {message_type, *SMS_MESSAGE_TYPE_ALIASES.get(message_type, set())}
    if message_type != "phone_verification" and allowed_types and allowed_types.isdisjoint(message_type_aliases):
        return False, "This SMS notification type is disabled."
    return True, ""


def _find_existing_delivery(*, dedupe_key: str) -> SMSDelivery | None:
    if not dedupe_key:
        return None
    return SMSDelivery.objects.filter(
        dedupe_key=dedupe_key,
        status__in=[SMSDelivery.Status.QUEUED, SMSDelivery.Status.SENDING, SMSDelivery.Status.SENT, SMSDelivery.Status.DELIVERED],
    ).first()


def _create_delivery_record(
    *,
    user=None,
    phone_number: str,
    message_type: str,
    message_body: str,
    metadata: dict[str, Any] | None = None,
    related_object_type: str = "",
    related_object_id: str = "",
    dedupe_key: str = "",
    status: str = SMSDelivery.Status.QUEUED,
    error_message: str = "",
    source: str = "",
) -> SMSDelivery:
    return SMSDelivery.objects.create(
        user=user,
        phone_number=phone_number,
        message_type=message_type,
        message_body=sanitize_sms_message(message_body, limit=640),
        metadata=metadata or {},
        related_object_type=related_object_type,
        related_object_id=related_object_id,
        dedupe_key=dedupe_key,
        status=status,
        error_message=error_message[:2000],
        source=source[:64],
        failed_at=timezone.now() if status == SMSDelivery.Status.FAILED else None,
    )


def mark_sms_delivery_sending(*, delivery: SMSDelivery) -> SMSDelivery:
    delivery.status = SMSDelivery.Status.SENDING
    delivery.retry_count += 1
    delivery.error_message = ""
    delivery.save(update_fields=["status", "retry_count", "error_message", "updated_at"])
    return delivery


def mark_sms_delivery_sent(*, delivery: SMSDelivery, provider_response: dict[str, Any]) -> SMSDelivery:
    resolved_status = str(provider_response.get("status", "")).strip().lower()
    is_delivered = resolved_status == SMSDelivery.Status.DELIVERED
    delivery.status = SMSDelivery.Status.DELIVERED if is_delivered else SMSDelivery.Status.SENT
    delivery.provider = str(provider_response.get("provider", ""))[:32]
    delivery.provider_message_id = str(provider_response.get("message_id", ""))[:255]
    delivery.provider_response = provider_response
    delivery.sent_at = timezone.now()
    delivery.delivered_at = timezone.now() if is_delivered else delivery.delivered_at
    delivery.error_message = ""
    delivery.save(
        update_fields=[
            "status",
            "provider",
            "provider_message_id",
            "provider_response",
            "sent_at",
            "delivered_at",
            "error_message",
            "updated_at",
        ]
    )
    return delivery


def mark_sms_delivery_failed(*, delivery: SMSDelivery, message: str) -> SMSDelivery:
    delivery.status = SMSDelivery.Status.FAILED
    delivery.error_message = str(message)[:2000]
    delivery.failed_at = timezone.now()
    delivery.save(update_fields=["status", "error_message", "failed_at", "updated_at"])
    return delivery


def mark_sms_delivery_skipped(*, delivery: SMSDelivery, message: str) -> SMSDelivery:
    delivery.status = SMSDelivery.Status.SKIPPED
    delivery.error_message = str(message)[:2000]
    delivery.failed_at = timezone.now()
    delivery.save(update_fields=["status", "error_message", "failed_at", "updated_at"])
    return delivery


def deliver_sms_message(*, to: str, message: str, metadata: dict[str, Any] | None = None, provider_name: str | None = None) -> dict[str, Any]:
    provider = get_sms_provider(provider_name=provider_name)
    return provider.send_sms(to=to, message=sanitize_sms_message(message), metadata=metadata or {})


def _log_sms_action(*, actor=None, action: str, delivery: SMSDelivery, metadata: dict[str, Any] | None = None) -> None:
    create_audit_log(
        actor=actor,
        action=action,
        target_type="sms_delivery",
        target_id=str(delivery.id),
        target_repr=delivery.phone_number,
        metadata=build_audit_metadata(
            message_type=delivery.message_type,
            phone_number=delivery.phone_number,
            status=delivery.status,
            related_object_type=delivery.related_object_type,
            related_object_id=delivery.related_object_id,
            **(metadata or {}),
        ),
    )


def queue_sms(
    *,
    user=None,
    phone_number: str,
    message_type: str,
    message_body: str,
    metadata: dict[str, Any] | None = None,
    related_object_type: str = "",
    related_object_id: str = "",
    dedupe_key: str = "",
    actor=None,
    force: bool = False,
    source: str = "",
) -> SMSDelivery:
    existing = _find_existing_delivery(dedupe_key=dedupe_key)
    if existing is not None:
        return existing

    requested_phone = str(phone_number or getattr(user, "phone_number", "") or "").strip()
    can_send, reason = should_send_sms_for_user(user=user, message_type=message_type, force=force)
    if not can_send:
        delivery = _create_delivery_record(
            user=user,
            phone_number=requested_phone[:32],
            message_type=message_type,
            message_body=message_body,
            metadata=metadata,
            related_object_type=related_object_type,
            related_object_id=related_object_id,
            dedupe_key=dedupe_key,
            status=SMSDelivery.Status.SKIPPED,
            error_message=reason,
            source=source,
        )
        _log_sms_action(actor=actor, action=AuditAction.SMS_FAILED, delivery=delivery, metadata={"reason": reason, "skipped": True})
        return delivery

    try:
        resolved_phone = normalize_phone_number(
            requested_phone,
            getattr(user, "phone_country_code", None),
        )
    except ValueError as exc:
        error_message = sanitize_provider_error(exc, fallback_message="The recipient phone number is invalid.")
        delivery = _create_delivery_record(
            user=user,
            phone_number=requested_phone[:32],
            message_type=message_type,
            message_body=message_body,
            metadata=metadata,
            related_object_type=related_object_type,
            related_object_id=related_object_id,
            dedupe_key=dedupe_key,
            status=SMSDelivery.Status.FAILED if force else SMSDelivery.Status.SKIPPED,
            error_message=error_message,
            source=source,
        )
        _log_sms_action(
            actor=actor,
            action=AuditAction.SMS_FAILED,
            delivery=delivery,
            metadata={"reason": error_message, "invalid_phone": True, "skipped": not force},
        )
        return delivery

    delivery = _create_delivery_record(
        user=user,
        phone_number=resolved_phone,
        message_type=message_type,
        message_body=message_body,
        metadata=metadata,
        related_object_type=related_object_type,
        related_object_id=related_object_id,
        dedupe_key=dedupe_key,
        source=source,
    )

    def on_commit() -> None:
        from apps.notifications.tasks import deliver_sms_task

        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) or not connection.in_atomic_block:
            try:
                mark_sms_delivery_sending(delivery=delivery)
                provider_response = deliver_sms_message(to=delivery.phone_number, message=delivery.message_body, metadata=delivery.metadata)
            except SMSSendFailedError as exc:
                error_message = sanitize_provider_error(exc, fallback_message="SMS delivery failed.")
                mark_sms_delivery_failed(delivery=delivery, message=error_message)
                _log_sms_action(actor=actor, action=AuditAction.SMS_FAILED, delivery=delivery, metadata={"reason": error_message})
                return
            mark_sms_delivery_sent(delivery=delivery, provider_response=provider_response)
            _log_sms_action(actor=actor, action=AuditAction.SMS_SENT, delivery=delivery, metadata={"provider": delivery.provider})
            return

        try:
            async_result = deliver_sms_task.delay(str(delivery.id))
            SMSDelivery.objects.filter(id=delivery.id).update(celery_task_id=str(async_result.id or ""))
        except Exception:
            logger.exception("sms_queue_failed", extra={"delivery_id": str(delivery.id), "message_type": message_type})
            mark_sms_delivery_failed(delivery=delivery, message="SMS delivery could not be queued.")
            _log_sms_action(actor=actor, action=AuditAction.SMS_FAILED, delivery=delivery, metadata={"reason": "queue_failed"})

    _log_sms_action(actor=actor, action=AuditAction.SMS_QUEUED, delivery=delivery)
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) or not connection.in_atomic_block:
        on_commit()
    else:
        transaction.on_commit(on_commit)
    return delivery
