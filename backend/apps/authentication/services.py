from __future__ import annotations

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
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
from apps.integrations.email.services import queue_password_reset_email, queue_welcome_email
from apps.integrations.exceptions import OAuthValidationFailedError
from apps.integrations.oauth.services import (
    get_google_oauth_config as get_google_oauth_config_payload,
    handle_google_auth_request,
)
from apps.users.models import User as UserModel
from apps.users.selectors import get_user_by_email

User = get_user_model()


def create_user_account(
    *,
    name: str,
    email: str,
    password: str,
    first_name: str = "",
    last_name: str = "",
    auth_provider: str = UserModel.AuthProvider.EMAIL,
):
    user = User.objects.create_user(
        email=email,
        password=password,
        name=name,
        first_name=first_name,
        last_name=last_name,
        auth_provider=auth_provider,
        email_verified=auth_provider == UserModel.AuthProvider.GOOGLE,
    )
    log_auth_action(
        actor=user,
        action=AuditAction.USER_REGISTERED,
        target=user,
        metadata=build_audit_metadata(email=user.email, auth_provider=auth_provider),
    )
    if getattr(settings, "WELCOME_EMAIL_ENABLED", False):
        queue_welcome_email(user=user, actor=user)
    return user


def record_login_activity(*, email: str, request, success: bool, user=None, failure_reason: str = "") -> None:
    LoginActivity.objects.create(
        user=user,
        email=email,
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:1000],
        success=success,
        failure_reason=failure_reason[:255],
    )


def authenticate_user(*, email: str, password: str, request):
    user = authenticate(request=request, username=email, password=password)
    if user is None:
        record_login_activity(
            email=email,
            request=request,
            success=False,
            failure_reason="Invalid email or password.",
        )
        log_auth_action(
            action=AuditAction.USER_LOGIN_FAILED,
            target_repr=email.strip().lower(),
            metadata=build_audit_metadata(email=email.strip().lower(), failure_reason="Invalid email or password."),
        )
        raise exceptions.AuthenticationFailed("Invalid email or password.")
    if not user.is_active:
        record_login_activity(
            email=email,
            request=request,
            success=False,
            user=user,
            failure_reason="Account is inactive.",
        )
        log_auth_action(
            actor=user,
            action=AuditAction.USER_LOGIN_FAILED,
            target=user,
            metadata=build_audit_metadata(email=user.email, failure_reason="Account is inactive."),
        )
        raise exceptions.AuthenticationFailed("This account is inactive.")

    record_login_activity(email=email, request=request, success=True, user=user)
    update_last_login(None, user)
    log_auth_action(
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


def clear_refresh_cookie(response) -> None:
    response.delete_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        samesite=settings.AUTH_COOKIE_SAMESITE,
    )


def send_password_reset_email(*, user, request) -> None:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_base_url = getattr(settings, "PASSWORD_RESET_LINK_BASE_URL", f"{settings.FRONTEND_URL.rstrip('/')}/reset-password").rstrip("/")
    reset_url = f"{reset_base_url}?uid={uid}&token={token}"
    queue_password_reset_email(user=user, reset_url=reset_url, actor=user)


def request_password_reset(*, email: str, request) -> None:
    user = get_user_by_email(email=email)
    if user and user.is_active:
        send_password_reset_email(user=user, request=request)
        log_auth_action(
            actor=user,
            action=AuditAction.PASSWORD_RESET_REQUESTED,
            target=user,
            metadata=build_audit_metadata(email=user.email),
        )


def confirm_password_reset(*, user, new_password: str) -> None:
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    log_auth_action(
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
    log_auth_action(
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
