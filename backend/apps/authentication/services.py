from __future__ import annotations

import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, log_auth_action
from apps.common.ip import normalize_client_ip
from rest_framework import exceptions

from apps.authentication.models import CredentialChangeRequest, LoginActivity
from apps.authentication.models import AuthSession, EmailVerificationToken, PhoneVerificationCode
from apps.authentication.providers import GoogleOAuthProvider
from apps.authentication.tokens import blacklist_token, create_token_pair_for_user, get_refresh_token_max_age
from apps.integrations.email.builders import _get_frontend_url, _is_public_absolute_url
from apps.integrations.email.services import (
    queue_credential_change_email,
    queue_email_verification_email,
    queue_password_reset_email,
    queue_welcome_email,
)
from apps.integrations.exceptions import OAuthValidationFailedError
from apps.integrations.sms.services import (
    generate_phone_verification_code,
    infer_phone_country_code,
    normalize_phone_number,
    queue_sms,
)
from apps.integrations.oauth.services import (
    get_google_oauth_config as get_google_oauth_config_payload,
    handle_google_auth_request,
)
from apps.users.models import User as UserModel
from apps.teams.services import create_team_with_owner
from apps.users.selectors import get_user_by_email, get_user_by_phone

User = get_user_model()
logger = logging.getLogger(__name__)


def _normalize_auth_email(email: str) -> str:
    return (email or "").strip().lower()


def _normalize_auth_phone(phone_number: str, country_code: str | None = None) -> str:
    return normalize_phone_number(phone_number=phone_number, country_code=country_code)


def validate_selected_account_type(*, user, account_type: str) -> None:
    if not account_type:
        return
    if getattr(user, "account_type", UserModel.AccountType.PERSONAL) != account_type:
        raise exceptions.AuthenticationFailed("Selected workspace mode does not match this account.")


def resolve_auth_identity(*, credential: str) -> tuple[str, str]:
    normalized_credential = (credential or "").strip()
    if "@" in normalized_credential:
        return "email", _normalize_auth_email(normalized_credential)
    try:
        return "phone", _normalize_auth_phone(normalized_credential)
    except ValueError:
        raise exceptions.AuthenticationFailed("Invalid phone number or password.")


def _safe_queue_welcome_email(*, user) -> None:
    if not getattr(user, "email", ""):
        return
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
    email: str = "",
    phone_number: str = "",
    phone_country_code: str = "",
    password: str,
    first_name: str = "",
    last_name: str = "",
    auth_provider: str = UserModel.AuthProvider.EMAIL,
    account_type: str = UserModel.AccountType.PERSONAL,
    team_name: str = "",
):
    normalized_email = _normalize_auth_email(email) if email else None
    normalized_phone = _normalize_auth_phone(phone_number, phone_country_code) if phone_number else None
    resolved_phone_country_code = phone_country_code or (infer_phone_country_code(normalized_phone) if normalized_phone else "")
    resolved_provider = auth_provider
    if resolved_provider == UserModel.AuthProvider.EMAIL and normalized_phone and not normalized_email:
        resolved_provider = UserModel.AuthProvider.PHONE

    user = User.objects.create_user(
        email=normalized_email,
        phone_number=normalized_phone,
        phone_country_code=resolved_phone_country_code,
        password=password,
        name=name,
        first_name=first_name,
        last_name=last_name,
        auth_provider=resolved_provider,
        email_verified=auth_provider == UserModel.AuthProvider.GOOGLE,
        phone_verified=False,
        sms_opt_in=bool(normalized_phone),
        account_type=account_type,
        primary_mode=account_type,
        onboarding_completed=True,
    )

    if account_type == UserModel.AccountType.PERSONAL:
        personal_team_name = team_name.strip() or f"{name.strip()}'s Personal Workspace"
        create_team_with_owner(created_by=user, name=personal_team_name, is_personal=True)
    elif account_type == UserModel.AccountType.TEAM:
        team_label = team_name.strip() or f"{name.strip()}'s Team"
        create_team_with_owner(created_by=user, name=team_label, is_personal=False)
    _safe_log_auth_action(
        actor=user,
        action=AuditAction.USER_REGISTERED,
        target=user,
        metadata=build_audit_metadata(email=user.email, phone_number=user.phone_number, auth_provider=resolved_provider),
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


def authenticate_user(*, credential: str | None = None, password: str, request, email: str | None = None, account_type: str = ""):
    resolved_credential = credential or email
    if not resolved_credential:
        raise exceptions.AuthenticationFailed("A login credential is required.")
    identifier_type, normalized_credential = resolve_auth_identity(credential=resolved_credential)
    if identifier_type == "email":
        user = get_user_by_email(email=normalized_credential)
    else:
        user = get_user_by_phone(phone_number=normalized_credential)
    if user is None or not user.check_password(password):
        user = None
    if user is None:
        recent_change_message = get_recent_credential_change_message(
            identifier_type=identifier_type,
            credential_value=normalized_credential,
        )
        failure_message = recent_change_message or "Invalid phone number or password."
        record_login_activity(
            email=normalized_credential,
            request=request,
            success=False,
            failure_reason=failure_message,
        )
        _safe_log_auth_action(
            action=AuditAction.USER_LOGIN_FAILED,
            target_repr=normalized_credential.lower() if isinstance(normalized_credential, str) else "",
            metadata=build_audit_metadata(
                credential=normalized_credential,
                identifier_type=identifier_type,
                failure_reason=failure_message,
            ),
        )
        raise exceptions.AuthenticationFailed(failure_message)
    if not user.is_active:
        record_login_activity(
            email=normalized_credential,
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

    validate_selected_account_type(user=user, account_type=account_type)

    record_login_activity(email=normalized_credential, request=request, success=True, user=user)
    try:
        update_last_login(None, user)
    except Exception:
        logger.exception("Unable to update last_login", extra={"user_id": str(getattr(user, "pk", ""))})
    _safe_log_auth_action(
        actor=user,
        action=AuditAction.USER_LOGGED_IN,
        target=user,
        metadata=build_audit_metadata(
            email=user.email,
            phone_number=user.phone_number,
            auth_provider=user.auth_provider,
            identifier_type=identifier_type,
        ),
    )
    return user


def issue_tokens_for_user(*, user, remember_me: bool = False) -> dict:
    return create_token_pair_for_user(user=user, remember_me=remember_me)


def authenticate_user_and_issue_tokens(*, credential: str, password: str, request, account_type: str = "", remember_me: bool = False) -> tuple:
    user = authenticate_user(credential=credential, password=password, request=request, account_type=account_type)
    token_payload = issue_tokens_for_user(user=user, remember_me=remember_me)
    register_auth_session(user=user, token_payload=token_payload, request=request)
    return user, token_payload


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


def _get_email_verification_link(*, token: str) -> str:
    frontend_base_url = _get_frontend_url()
    if frontend_base_url:
        return f"{frontend_base_url}/verify-email?token={token}"
    return token


def create_email_verification_token(*, user) -> EmailVerificationToken:
    EmailVerificationToken.objects.filter(user=user, used_at__isnull=True).delete()
    return EmailVerificationToken.objects.create(
        user=user,
        token=secrets.token_urlsafe(32),
        expires_at=timezone.now() + timedelta(days=2),
    )


def send_email_verification(*, user, actor=None):
    if user.email_verified or not user.email:
        return None
    token = create_email_verification_token(user=user)
    return queue_email_verification_email(
        user=user,
        verification_url=_get_email_verification_link(token=token.token),
        actor=actor or user,
    )


def verify_email_address(*, token: str):
    verification = EmailVerificationToken.objects.select_related("user").filter(token=token, used_at__isnull=True).first()
    if verification is None or verification.expires_at <= timezone.now():
        raise exceptions.ValidationError({"token": "Verification token is invalid or expired."})

    verification.used_at = timezone.now()
    verification.save(update_fields=["used_at", "updated_at"])
    user = verification.user
    if not user.email_verified:
        user.email_verified = True
        user.save(update_fields=["email_verified", "updated_at"])
        _safe_log_auth_action(
            actor=user,
            action=AuditAction.ACCOUNT_LINKED,
            target=user,
            metadata=build_audit_metadata(email=user.email, event="email_verified"),
        )
    return user


def _resolve_device_name(*, request) -> str:
    user_agent = str(request.META.get("HTTP_USER_AGENT", "") or "").strip()
    return user_agent[:255] if user_agent else "Unknown device"


def register_auth_session(*, user, token_payload: dict, request) -> AuthSession:
    return AuthSession.objects.create(
        user=user,
        refresh_token_jti=token_payload["refresh_jti"],
        device_name=_resolve_device_name(request=request),
        ip_address=get_client_ip(request),
        user_agent=str(request.META.get("HTTP_USER_AGENT", "") or "")[:1000],
        last_seen_at=timezone.now(),
        expires_at=token_payload["refresh_expires_at"],
    )


def get_auth_session_from_token(*, token_value: str) -> AuthSession | None:
    from rest_framework_simplejwt.tokens import RefreshToken, TokenError

    try:
        refresh = RefreshToken(token_value)
        return AuthSession.objects.filter(refresh_token_jti=str(refresh["jti"])).first()
    except TokenError:
        return None


def ensure_auth_session_is_active(*, token_value: str) -> AuthSession:
    session = get_auth_session_from_token(token_value=token_value)
    if session is None:
        raise exceptions.ValidationError({"refresh": "Session could not be found."})
    if session.status != AuthSession.Status.ACTIVE or session.revoked_at is not None or session.expires_at <= timezone.now():
        raise exceptions.ValidationError({"refresh": "This session has expired or been revoked."})
    return session


def rotate_auth_session(*, session: AuthSession, token_payload: dict, request) -> AuthSession:
    session.refresh_token_jti = token_payload["refresh_jti"]
    session.ip_address = get_client_ip(request)
    session.user_agent = str(request.META.get("HTTP_USER_AGENT", "") or "")[:1000]
    session.device_name = _resolve_device_name(request=request)
    session.last_seen_at = timezone.now()
    session.expires_at = token_payload["refresh_expires_at"]
    session.status = AuthSession.Status.ACTIVE
    session.revoked_at = None
    session.save(
        update_fields=[
            "refresh_token_jti",
            "ip_address",
            "user_agent",
            "device_name",
            "last_seen_at",
            "expires_at",
            "status",
            "revoked_at",
            "updated_at",
        ]
    )
    return session


def get_user_sessions(*, user):
    expired_ids = list(
        AuthSession.objects.filter(user=user, status=AuthSession.Status.ACTIVE, expires_at__lte=timezone.now()).values_list("id", flat=True)
    )
    if expired_ids:
        AuthSession.objects.filter(id__in=expired_ids).update(status=AuthSession.Status.EXPIRED, updated_at=timezone.now())
    return AuthSession.objects.filter(user=user).order_by("-last_seen_at", "-created_at")


def revoke_auth_session(*, session: AuthSession) -> AuthSession:
    if session.status != AuthSession.Status.REVOKED:
        session.status = AuthSession.Status.REVOKED
        session.revoked_at = timezone.now()
        session.save(update_fields=["status", "revoked_at", "updated_at"])
    return session


def revoke_auth_session_for_token(*, token_value: str) -> AuthSession | None:
    session = get_auth_session_from_token(token_value=token_value)
    if session is None:
        return None
    return revoke_auth_session(session=session)


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


def create_phone_verification_code(*, user) -> PhoneVerificationCode:
    if not user.phone_number:
        raise exceptions.ValidationError({"phone_number": "Add a phone number before requesting verification."})
    PhoneVerificationCode.objects.filter(user=user, used_at__isnull=True).delete()
    return PhoneVerificationCode.objects.create(
        user=user,
        phone_number=user.phone_number,
        code=generate_phone_verification_code(),
        expires_at=timezone.now() + timedelta(minutes=10),
    )


def request_phone_verification(*, user, actor=None) -> PhoneVerificationCode:
    verification = create_phone_verification_code(user=user)
    queue_sms(
        user=user,
        phone_number=user.phone_number,
        message_type="phone_verification",
        message_body=f"{getattr(settings, 'APP_NAME', 'WorkNest')}: your verification code is {verification.code}. It expires in 10 minutes.",
        metadata={"phone_verification_id": str(verification.id)},
        related_object_type="phone_verification",
        related_object_id=str(verification.id),
        dedupe_key=f"phone-verification:{user.id}:{verification.code}",
        actor=actor or user,
        force=True,
        source="authentication.phone_verification",
    )
    return verification


def confirm_phone_verification(*, user, code: str):
    verification = (
        PhoneVerificationCode.objects.filter(
            user=user,
            phone_number=user.phone_number,
            code=str(code or "").strip(),
            used_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )
    if verification is None or verification.expires_at <= timezone.now():
        raise exceptions.ValidationError({"code": "Verification code is invalid or expired."})

    verification.attempt_count += 1
    verification.used_at = timezone.now()
    verification.save(update_fields=["attempt_count", "used_at", "updated_at"])

    if not user.phone_verified:
        user.phone_verified = True
        user.phone_country_code = infer_phone_country_code(user.phone_number or "")
        user.save(update_fields=["phone_verified", "phone_country_code", "updated_at"])
        _safe_log_auth_action(
            actor=user,
            action=AuditAction.PHONE_VERIFIED,
            target=user,
            metadata=build_audit_metadata(phone_number=user.phone_number),
        )
    return user


def _recent_credential_change_window() -> timedelta:
    return timedelta(days=7)


def _expire_active_credential_change_requests(*, user, credential_type: str) -> None:
    CredentialChangeRequest.objects.filter(
        user=user,
        credential_type=credential_type,
        used_at__isnull=True,
        expires_at__gt=timezone.now(),
    ).update(used_at=timezone.now(), updated_at=timezone.now())


def _build_phone_change_message(*, code: str) -> str:
    return (
        f"{getattr(settings, 'APP_NAME', 'WorkNest')}: use verification code {code} to confirm your new phone number. "
        "It expires in 10 minutes."
    )


def _get_active_credential_change_request(*, user, credential_type: str) -> CredentialChangeRequest | None:
    return (
        CredentialChangeRequest.objects.filter(
            user=user,
            credential_type=credential_type,
            used_at__isnull=True,
            expires_at__gt=timezone.now(),
        )
        .order_by("-created_at")
        .first()
    )


def request_email_change(*, user, new_email: str, actor=None) -> CredentialChangeRequest:
    normalized_email = _normalize_auth_email(new_email)
    if not normalized_email:
        raise exceptions.ValidationError({"new_value": "Email is required."})
    if normalized_email == _normalize_auth_email(getattr(user, "email", "")):
        raise exceptions.ValidationError({"new_value": "This is already your current email address."})
    if User.objects.exclude(pk=user.pk).filter(email__iexact=normalized_email).exists():
        raise exceptions.ValidationError({"new_value": "Email is already registered."})

    _expire_active_credential_change_requests(user=user, credential_type=CredentialChangeRequest.CredentialType.EMAIL)
    change_request = CredentialChangeRequest.objects.create(
        user=user,
        credential_type=CredentialChangeRequest.CredentialType.EMAIL,
        current_value=_normalize_auth_email(getattr(user, "email", "")),
        new_value=normalized_email,
        code=generate_phone_verification_code(),
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    queue_credential_change_email(user=user, new_email=normalized_email, code=change_request.code, actor=actor or user)
    return change_request


def request_phone_change(*, user, new_phone_number: str, phone_country_code: str = "", actor=None) -> CredentialChangeRequest:
    normalized_phone = _normalize_auth_phone(new_phone_number, phone_country_code)
    current_phone_number = getattr(user, "phone_number", "") or ""
    if current_phone_number and normalized_phone == _normalize_auth_phone(current_phone_number, getattr(user, "phone_country_code", "")):
        raise exceptions.ValidationError({"new_value": "This is already your current phone number."})
    if User.objects.exclude(pk=user.pk).filter(phone_number=normalized_phone).exists():
        raise exceptions.ValidationError({"new_value": "Phone number is already registered."})

    _expire_active_credential_change_requests(user=user, credential_type=CredentialChangeRequest.CredentialType.PHONE)
    change_request = CredentialChangeRequest.objects.create(
        user=user,
        credential_type=CredentialChangeRequest.CredentialType.PHONE,
        current_value=getattr(user, "phone_number", "") or "",
        new_value=normalized_phone,
        code=generate_phone_verification_code(),
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    queue_sms(
        user=user,
        phone_number=normalized_phone,
        message_type="phone_verification",
        message_body=_build_phone_change_message(code=change_request.code),
        metadata={"credential_change_request_id": str(change_request.id)},
        related_object_type="credential_change_request",
        related_object_id=str(change_request.id),
        dedupe_key=f"credential-change-phone:{user.id}:{change_request.code}",
        actor=actor or user,
        force=True,
        source="authentication.credential_change_phone",
    )
    return change_request


def request_credential_change(*, user, credential_type: str, new_value: str, phone_country_code: str = "", actor=None) -> CredentialChangeRequest:
    if credential_type == CredentialChangeRequest.CredentialType.EMAIL:
        return request_email_change(user=user, new_email=new_value, actor=actor)
    if credential_type == CredentialChangeRequest.CredentialType.PHONE:
        return request_phone_change(user=user, new_phone_number=new_value, phone_country_code=phone_country_code, actor=actor)
    raise exceptions.ValidationError({"credential_type": "Unsupported credential type."})


def confirm_credential_change(*, user, credential_type: str, code: str):
    change_request = _get_active_credential_change_request(user=user, credential_type=credential_type)
    if change_request is None:
        raise exceptions.ValidationError({"code": "There is no active verification request for this change."})

    submitted_code = str(code or "").strip()
    if change_request.code != submitted_code:
        change_request.attempt_count += 1
        change_request.save(update_fields=["attempt_count", "updated_at"])
        raise exceptions.ValidationError({"code": "Verification code is invalid or expired."})

    if change_request.expires_at <= timezone.now():
        raise exceptions.ValidationError({"code": "Verification code is invalid or expired."})

    updated_fields: list[str] = []
    if credential_type == CredentialChangeRequest.CredentialType.EMAIL:
        if User.objects.exclude(pk=user.pk).filter(email__iexact=change_request.new_value).exists():
            raise exceptions.ValidationError({"new_value": "Email is already registered."})
        user.email = change_request.new_value
        user.email_verified = True
        updated_fields.extend(["email", "email_verified"])
        _safe_log_auth_action(
            actor=user,
            action=AuditAction.EMAIL_UPDATED,
            target=user,
            metadata=build_audit_metadata(previous_email=change_request.current_value, email=change_request.new_value),
        )
    elif credential_type == CredentialChangeRequest.CredentialType.PHONE:
        if User.objects.exclude(pk=user.pk).filter(phone_number=change_request.new_value).exists():
            raise exceptions.ValidationError({"new_value": "Phone number is already registered."})
        user.phone_number = change_request.new_value
        user.phone_verified = True
        user.phone_country_code = infer_phone_country_code(change_request.new_value)
        updated_fields.extend(["phone_number", "phone_verified", "phone_country_code"])
        _safe_log_auth_action(
            actor=user,
            action=AuditAction.PHONE_UPDATED,
            target=user,
            metadata=build_audit_metadata(previous_phone_number=change_request.current_value, phone_number=change_request.new_value),
        )
    else:
        raise exceptions.ValidationError({"credential_type": "Unsupported credential type."})

    change_request.attempt_count += 1
    change_request.used_at = timezone.now()
    change_request.save(update_fields=["attempt_count", "used_at", "updated_at"])
    user.save(update_fields=[*updated_fields, "updated_at"])
    return user


def get_recent_credential_change_message(*, identifier_type: str, credential_value: str) -> str | None:
    normalized_value = str(credential_value or "").strip()
    if not normalized_value:
        return None
    if identifier_type == "email":
        normalized_value = _normalize_auth_email(normalized_value)
        credential_type = CredentialChangeRequest.CredentialType.EMAIL
        label = "email address"
    else:
        credential_type = CredentialChangeRequest.CredentialType.PHONE
        label = "phone number"

    recently_changed = CredentialChangeRequest.objects.filter(
        credential_type=credential_type,
        current_value=normalized_value,
        used_at__gte=timezone.now() - _recent_credential_change_window(),
    ).exists()
    if not recently_changed:
        return None
    return f"Your {label} was recently changed. Sign in with your updated details."


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
