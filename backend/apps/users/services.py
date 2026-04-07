from __future__ import annotations

import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import OperationalError, ProgrammingError

from apps.users.models import User
from apps.users.selectors import get_current_user_profile


def bootstrap_admin_user(*, email: str | None = None, name: str | None = None, password: str | None = None) -> tuple[User, bool]:
    resolved_email = str(email or getattr(settings, "ADMIN_EMAIL", "admin@worknest.local")).strip().lower() or "admin@worknest.local"
    resolved_name = str(name or getattr(settings, "ADMIN_NAME", "WorkNest Admin")).strip() or "WorkNest Admin"
    resolved_password = str(password or getattr(settings, "ADMIN_PASSWORD", "WorkNest123!")).strip() or "WorkNest123!"

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
        return bootstrap_admin_user()
    except (OperationalError, ProgrammingError):
        return None


def update_user_profile(*, user: User, data: dict, request=None) -> User:
    updated_fields = []
    for field in ("name", "first_name", "last_name", "avatar", "bio", "timezone", "notification_preferences"):
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
