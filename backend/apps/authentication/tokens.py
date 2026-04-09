from __future__ import annotations

from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken, TokenError


def create_token_pair_for_user(*, user, remember_me: bool = False) -> dict:
    refresh = RefreshToken.for_user(user)
    refresh_lifetime = settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]
    if remember_me:
        refresh.set_exp(lifetime=refresh_lifetime * 2)

    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "refresh_jti": str(refresh["jti"]),
        "refresh_expires_at": datetime.fromtimestamp(refresh["exp"], tz=dt_timezone.utc),
        "refresh_expires_in": int((refresh_lifetime * 2 if remember_me else refresh_lifetime).total_seconds()),
        "token_type": "Bearer",
    }


def get_refresh_token_max_age(refresh_token: str) -> int:
    token = RefreshToken(refresh_token)
    return max(int(token["exp"] - timezone.now().timestamp()), 0)


def blacklist_token(token: str) -> None:
    try:
        RefreshToken(token).blacklist()
    except TokenError:
        pass


def get_user_id_from_refresh_token(token: str):
    refresh = RefreshToken(token)
    return refresh["user_id"]
