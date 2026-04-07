from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, log_auth_action
from apps.common.ip import normalize_client_ip
from rest_framework import exceptions

from apps.authentication.models import LoginActivity
from apps.authentication.providers import GoogleOAuthProvider
from apps.authentication.tokens import blacklist_token, create_token_pair_for_user, get_refresh_token_max_age
from apps.integrations.email.builders import _get_frontend_url, _is_public_absolute_url
from apps.integrations.email.services import queue_password_reset_email, queue_welcome_email
from apps.integrations.exceptions import OAuthValidationFailedError
from apps.integrations.oauth.services import (
    get_google_oauth_config as get_google_oauth_config_payload,
    handle_google_auth_request,
)
from apps.users.models import User as UserModel
from apps.users.selectors import get_user_by_email

User = get_user_model()
logger = logging.getLogger(__name__)


def _normalize_auth_email(email: str) -> str:
    return (email or "").strip()


def _safe_queue_welcome_email(*, user) -> None:
    try:
        queue_welcome_email(user=user, actor=user)
    except Exception:
        logger.exception("Unable to queue welcome email", extra={"user_id": str(getattr(user, "pk", ""))})


def sync_google_account_profile(
    *,
    user,
    name: str = "",
    first_name: str = "",
    last_name: str = "",
    avatar: str = "",
    email_verified: bool = True,
    overwrite_profile: bool = False,
):
    updated_fields: list[str] = []

    if user.auth_provider != UserModel.AuthProvider.GOOGLE:
        user.auth_provider = UserModel.AuthProvider.GOOGLE
        updated_fields.append("auth_provider")

    if email_verified and not user.email_verified:
        user.email_verified = True
        updated_fields.append("email_verified")

    profile_updates = {
        "name": name.strip(),
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "avatar": avatar.strip(),
    }

    for field, value in profile_updates.items():
        if not value:
            continue
        current_value = getattr(user, field, "")
        should_update = overwrite_profile or not current_value
        if should_update and current_value != value:
            setattr(user, field, value)
            updated_fields.append(field)

    if updated_fields:
        user.save(update_fields=[*updated_fields, "updated_at"])

    return user


def create_user_account(
    *,
    name: str,
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
    auth_provider: str = UserModel.AuthProvider.EMAIL,
):
    normalized_email = _normalize_auth_email(email)
    user = User.objects.create_user(
        email=normalized_email,
        password=password,
        name=name,
        first_name=first_name,
        last_name=last_name,
        auth_provider=auth_provider,
        email_verified=auth_provider == UserModel.AuthProvider.GOOGLE,
    )
    _safe_log_auth_action(
        actor=user,
        action=AuditAction.USER_REGISTERED,
        target=user,
        metadata=build_audit_metadata(email=user.email, auth_provider=auth_provider),
    )
    if getattr(settings, "WELCOME_EMAIL_ENABLED", False):
        _safe_queue_welcome_email(user=user)
    return user


def record_login_activity(*, email: str, request, success: bool, user=None, failure_reason: str = "") -> None:
    try:
        LoginActivity.objects.create(
            user=user,
            email=email,
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
            success=success,
            failure_reason=failure_reason[:255],
        )
    except Exception:
        logger.exception("Unable to record login activity", extra={"email": email, "success": success})


def authenticate_user(*, email: str, password: str, request):
    normalized_email = _normalize_auth_email(email)
    user = get_user_by_email(email=normalized_email)
    if user is None or not user.check_password(password):
        user = None
    if user is None:
        record_login_activity(
            email=normalized_email,
            request=request,
            success=False,
            failure_reason="Invalid email or password.",
        )
        _safe_log_auth_action(
            action=AuditAction.USER_LOGIN_FAILED,
            target_repr=normalized_email.lower(),
            metadata=build_audit_metadata(email=normalized_email.lower(), failure_reason="Invalid email or password."),
        )
        raise exceptions.AuthenticationFailed("Invalid email or password.")
    if not user.is_active:
        record_login_activity(
            email=normalized_email,
            request=request,
            success=False,
            user=user,
            failure_reason="Account is inactive.",
        )
        _safe_log_auth_action(
            actor=user,
            action=AuditAction.USER_LOGIN_FAILED,
            target=user,
            metadata=build_audit_metadata(email=user.email, failure_reason="Account is inactive."),
        )
        raise exceptions.AuthenticationFailed("This account is inactive.")

    record_login_activity(email=normalized_email, request=request, success=True, user=user)
    try:
        update_last_login(None, user)
    except Exception:
        logger.exception("Unable to update last_login", extra={"user_id": str(getattr(user, "pk", ""))})
    _safe_log_auth_action(
        actor=user,
        action=AuditAction.USER_LOGGED_IN,
        target=user,
        metadata=build_audit_metadata(email=user.email, auth_provider=user.auth_provider),
    )
    return user


def issue_tokens_for_user(*, user, remember_me: bool = False) -> dict:
    return create_token_pair_for_user(user=user, remember_me=remember_me)


def authenticate_user_and_issue_tokens(*, email: str, password: str, request, remember_me: bool = False) -> tuple:
    user = authenticate_user(email=email, password=password, request=request)
    return user, issue_tokens_for_user(user=user, remember_me=remember_me)


def blacklist_refresh_token(token: str) -> None:
    blacklist_token(token)


def set_refresh_cookie(response, refresh_token: str) -> None:
    max_age = get_refresh_token_max_age(refresh_token)
    response.set_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=max_age,
        httponly=settings.AUTH_COOKIE_HTTPONLY,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
    )


def try_set_refresh_cookie(response, refresh_token: str) -> bool:
    try:
        set_refresh_cookie(response, refresh_token)
        return True
    except Exception:
        logger.exception("Unable to set refresh cookie")
        return False


def clear_refresh_cookie(response) -> None:
    response.delete_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


def send_password_reset_email(*, user, request) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    configured_reset_base_url = str(
        getattr(settings, "PASSWORD_RESET_LINK_BASE_URL", f"{settings.FRONTEND_URL.rstrip('/')}/reset-password")
    ).rstrip("/")
    if _is_public_absolute_url(configured_reset_base_url):
        reset_base_url = configured_reset_base_url
    else:
        frontend_base_url = _get_frontend_url()
        reset_base_url = f"{frontend_base_url}/reset-password" if frontend_base_url else configured_reset_base_url
    reset_url = f"{reset_base_url}?uid={uid}&token={token}"
    queue_password_reset_email(user=user, reset_url=reset_url, actor=user)


def request_password_reset(*, email: str, request) -> None:
    user = get_user_by_email(email=email)
    if user and user.is_active:
        try:
            send_password_reset_email(user=user, request=request)
        except Exception:
            logger.exception(
                "Unable to queue password reset email",
                extra={"user_id": str(getattr(user, "pk", "")), "email": user.email},
            )
        _safe_log_auth_action(
            actor=user,
            action=AuditAction.PASSWORD_RESET_REQUESTED,
            target=user,
            metadata=build_audit_metadata(email=user.email),
        )


def confirm_password_reset(*, user, new_password: str) -> None:
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    _safe_log_auth_action(
        actor=user,
        action=AuditAction.PASSWORD_RESET_CONFIRMED,
        target=user,
        metadata=build_audit_metadata(email=user.email),
    )


def get_client_ip(request) -> str | None:
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return normalize_client_ip(forwarded_for)
    return normalize_client_ip(request.META.get("REMOTE_ADDR"))


def get_google_oauth_config(*, request) -> dict:
    return get_google_oauth_config_payload(request=request)


def handle_google_auth(*, request) -> dict:
    try:
        payload = handle_google_auth_request(request=request)
    except OAuthValidationFailedError as exc:
        raise exceptions.ValidationError(str(exc)) from exc
    _safe_log_auth_action(
        action=AuditAction.GOOGLE_LOGIN_REQUESTED,
        target_repr="Google OAuth",
        metadata=build_audit_metadata(provider=GoogleOAuthProvider.name),
    )
    return payload


def normalize_token_value(token_value) -> str | None:
    if token_value is None:
        return None
    if hasattr(token_value, "value"):
        return token_value.value
    return str(token_value)


def _safe_log_auth_action(*, actor=None, action: str, target=None, metadata: dict | None = None, target_repr: str = "") -> None:
    try:
        log_auth_action(
            actor=actor,
            action=action,
            target=target,
            metadata=metadata,
            target_repr=target_repr,
        )
    except Exception:
        logger.exception(
            "Unable to write auth audit log",
            extra={"action": action, "actor_id": str(getattr(actor, "pk", "")), "target_repr": target_repr},
        )
