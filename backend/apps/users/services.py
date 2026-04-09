from __future__ import annotations

import uuid
from datetime import timedelta

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import OperationalError, ProgrammingError
from django.utils import timezone

from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, create_audit_log
from apps.integrations.sms.services import default_sms_preferences, infer_phone_country_code, normalize_phone_number
from apps.notifications.constants import NotificationType
from apps.users.models import PushDevice, User
from apps.users.selectors import get_current_user_profile


def bootstrap_admin_user(*, email: str | None = None, name: str | None = None, password: str | None = None) -> tuple[User, bool]:
    resolved_email = (
        str(email or getattr(settings, "ADMIN_EMAIL", "admin@example.com")).strip().lower()
        or "admin@example.com"
    )
    resolved_name = str(name or getattr(settings, "ADMIN_NAME", "WorkNest Admin")).strip() or "WorkNest Admin"
    resolved_password = str(password or getattr(settings, "ADMIN_PASSWORD", "ChangeMeNow123!")).strip() or "ChangeMeNow123!"

    user, created = User.objects.get_or_create(
        email=resolved_email,
        defaults={
            "name": resolved_name,
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
            "email_verified": True,
        },
    )

    updated_fields: list[str] = []
    expected_values = {
        "name": resolved_name,
        "is_staff": True,
        "is_superuser": True,
        "is_active": True,
        "email_verified": True,
    }
    for field, value in expected_values.items():
        if getattr(user, field) != value:
            setattr(user, field, value)
            updated_fields.append(field)

    user.set_password(resolved_password)
    updated_fields.append("password")
    user.save(update_fields=[*dict.fromkeys(updated_fields), "updated_at"])
    return user, created


def bootstrap_admin_user_from_settings() -> tuple[User, bool] | None:
    if str(getattr(settings, "ADMIN_BOOTSTRAP_ENABLED", "0")).strip() not in {"1", "true", "True"}:
        return None
    try:
        email = str(getattr(settings, "ADMIN_EMAIL", "")).strip().lower()
        password = str(getattr(settings, "ADMIN_PASSWORD", "")).strip()
        if not email or not password:
            raise ValueError("ADMIN_EMAIL and ADMIN_PASSWORD must be set when ADMIN_BOOTSTRAP_ENABLED is enabled.")
        name = str(getattr(settings, "ADMIN_NAME", "WorkNest Admin")).strip() or "WorkNest Admin"
        return bootstrap_admin_user(email=email, name=name, password=password)
    except (OperationalError, ProgrammingError):
        return None


def update_user_profile(*, user: User, data: dict, request=None) -> User:
    updated_fields = []
    for field in (
        "name",
        "first_name",
        "last_name",
        "avatar",
        "bio",
        "timezone",
        "notification_preferences",
        "security_preferences",
        "sms_preferences",
        "sms_opt_in",
        "theme_preference",
        "onboarding_completed",
    ):
        if field in data:
            setattr(user, field, data[field])
            updated_fields.append(field)

    avatar_file = data.get("avatar_file")
    if data.get("clear_avatar"):
        user.avatar = ""
        if "avatar" not in updated_fields:
            updated_fields.append("avatar")
    elif avatar_file is not None:
        extension = ""
        original_name = str(getattr(avatar_file, "name", "avatar") or "avatar")
        if "." in original_name:
            extension = f".{original_name.rsplit('.', 1)[-1].lower()}"
        storage_path = f"avatars/{user.id}/{uuid.uuid4().hex}{extension}"
        saved_path = default_storage.save(storage_path, avatar_file)
        media_url = f"{settings.MEDIA_URL.rstrip('/')}/{saved_path.lstrip('/')}"
        avatar_url = request.build_absolute_uri(media_url) if request is not None else media_url
        user.avatar = avatar_url
        if "avatar" not in updated_fields:
            updated_fields.append("avatar")

    user.save(update_fields=[*updated_fields, "updated_at"])
    return user


def get_user_profile(*, user: User) -> User:
    return get_current_user_profile(user=user)


def touch_user_presence(*, user: User, source: str = "web") -> None:
    if not getattr(user, "pk", None):
        return
    now = timezone.now()
    if user.last_seen_at and now - user.last_seen_at < timedelta(minutes=2) and user.last_seen_source == source:
        return
    User.objects.filter(pk=user.pk).update(last_seen_at=now, last_seen_source=(source or "web")[:64], updated_at=now)


def upsert_push_device(*, user: User, token: str, platform: str, label: str = "", app_version: str = "") -> PushDevice:
    device, _created = PushDevice.objects.update_or_create(
        user=user,
        token=token,
        defaults={
            "platform": platform,
            "label": label.strip(),
            "app_version": app_version.strip(),
            "is_active": True,
            "last_seen_at": timezone.now(),
        },
    )
    return device


def revoke_push_device(*, device: PushDevice) -> PushDevice:
    device.is_active = False
    device.last_seen_at = timezone.now()
    device.save(update_fields=["is_active", "last_seen_at", "updated_at"])
    return device


def update_phone_settings(*, user: User, phone_number: str, phone_country_code: str = "", sms_opt_in: bool | None = None) -> User:
    normalized_phone = normalize_phone_number(phone_number, phone_country_code)
    resolved_country_code = phone_country_code or infer_phone_country_code(normalized_phone)
    updated_fields: list[str] = []

    if user.phone_number != normalized_phone:
        user.phone_number = normalized_phone
        user.phone_verified = False
        updated_fields.extend(["phone_number", "phone_verified"])

    if user.phone_country_code != resolved_country_code:
        user.phone_country_code = resolved_country_code
        updated_fields.append("phone_country_code")

    if sms_opt_in is not None and user.sms_opt_in != sms_opt_in:
        user.sms_opt_in = bool(sms_opt_in)
        updated_fields.append("sms_opt_in")

    if updated_fields:
        user.save(update_fields=[*dict.fromkeys(updated_fields), "updated_at"])
        create_audit_log(
            actor=user,
            action=AuditAction.PHONE_UPDATED,
            target_type="user",
            target_id=str(user.id),
            target_repr=user.name or user.email or user.phone_number,
            metadata=build_audit_metadata(phone_number=user.phone_number, sms_opt_in=user.sms_opt_in),
        )
    return user


def update_notification_preferences(*, user: User, data: dict) -> User:
    notification_preferences = dict(user.notification_preferences or {})
    sms_preferences = default_sms_preferences()
    sms_preferences.update(user.sms_preferences or {})
    channels = notification_preferences.get("channels") if isinstance(notification_preferences.get("channels"), dict) else {}
    channel_in_app = {
        notification_type: bool((channels.get("in_app") or {}).get(notification_type, True))
        for notification_type in NotificationType.values
    }
    channel_email = {
        notification_type: bool((channels.get("email") or {}).get(notification_type, True))
        for notification_type in NotificationType.values
    }

    email_keys = {
        "mention_emails": NotificationType.MENTIONED_IN_COMMENT,
        "task_assignment_emails": NotificationType.TASK_ASSIGNED,
        "deadline_reminder_emails": NotificationType.DEADLINE_APPROACHING,
        "comment_emails": NotificationType.COMMENT_POSTED,
        "invite_emails": NotificationType.TEAM_INVITE,
        "admin_message_emails": NotificationType.ADMIN_MESSAGE,
    }
    sms_keys = {
        "mention_sms",
        "task_assignment_sms",
        "deadline_reminder_sms",
        "invite_sms",
        "broadcast_sms",
    }

    if "channels" in data and isinstance(data.get("channels"), dict):
        channels_payload = data.get("channels") or {}
        in_app_payload = channels_payload.get("in_app") or {}
        email_payload = channels_payload.get("email") or {}
        if isinstance(in_app_payload, dict):
            for key, value in in_app_payload.items():
                channel_in_app[str(key)] = bool(value)
        if isinstance(email_payload, dict):
            for key, value in email_payload.items():
                channel_email[str(key)] = bool(value)

    for key, value in data.items():
        if key in email_keys:
            channel_email[email_keys[key]] = bool(value)
        if key in sms_keys:
            sms_preferences[key] = bool(value)

    notification_preferences["channels"] = {"in_app": channel_in_app, "email": channel_email}
    for key, notification_type in email_keys.items():
        notification_preferences[key] = bool(channel_email.get(notification_type, True))
    user.notification_preferences = notification_preferences
    user.sms_preferences = sms_preferences
    user.save(update_fields=["notification_preferences", "sms_preferences", "updated_at"])
    create_audit_log(
        actor=user,
        action=AuditAction.SMS_PREFERENCES_UPDATED,
        target_type="user",
        target_id=str(user.id),
        target_repr=user.name or user.email or user.phone_number,
        metadata=build_audit_metadata(
            notification_preferences=notification_preferences,
            sms_preferences=sms_preferences,
        ),
    )
    return user
