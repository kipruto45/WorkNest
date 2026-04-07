from __future__ import annotations

from django.contrib.auth import get_user_model

User = get_user_model()


def get_current_user_profile(*, user):
    return User.objects.get(pk=user.pk)


def get_user_by_email(*, email: str):
    return User.objects.filter(email__iexact=email).first()
