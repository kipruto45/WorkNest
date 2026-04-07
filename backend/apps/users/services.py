from __future__ import annotations

import uuid

from django.conf import settings
from django.core.files.storage import default_storage

from apps.users.models import User
from apps.users.selectors import get_current_user_profile


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
