from __future__ import annotations

import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

logger = logging.getLogger(__name__)

from apps.authentication.permissions import AuthEntryPointPermission, AuthenticatedSessionPermission
from apps.authentication.adapter import build_google_callback_url, build_google_login_url
from apps.authentication.serializers import (
    AuthSessionSerializer,
    AuthTokenResponseSerializer,
    EmailVerificationRequestSerializer,
    GoogleOAuthConfigSerializer,
    GoogleOAuthLoginSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RefreshTokenSerializer,
    RegisterSerializer,
)
from apps.authentication.services import (
    authenticate_user,
    authenticate_user_and_issue_tokens,
    blacklist_refresh_token,
    clear_refresh_cookie,
    confirm_password_reset,
    create_user_account,
    ensure_auth_session_is_active,
    get_google_oauth_config,
    get_user_sessions,
    handle_google_auth,
    issue_tokens_for_user,
    normalize_token_value,
    register_auth_session,
    revoke_auth_session_for_token,
    revoke_auth_session,
    request_password_reset,
    rotate_auth_session,
    send_email_verification,
    set_refresh_cookie,
    try_set_refresh_cookie,
    verify_email_address,
)
from apps.authentication.throttles import LoginThrottle, PasswordResetThrottle, RegisterThrottle
from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, log_auth_action
from apps.common.responses import error_response, success_response
from apps.integrations.email.builders import _get_frontend_url
from apps.users.serializers import CurrentUserSerializer

User = get_user_model()


def _serialize_authenticated_user(user) -> dict:
    try:
        return CurrentUserSerializer(user).data
    except Exception:
        logger.exception(
            "Failed to serialize authenticated user payload",
            extra={"user_id": str(getattr(user, "pk", "")), "email": getattr(user, "email", "")},
        )
        return {
            "id": str(getattr(user, "id", "")),
            "email": getattr(user, "email", "") or "",
            "phone_number": getattr(user, "phone_number", "") or "",
            "phone_verified": bool(getattr(user, "phone_verified", False)),
            "name": getattr(user, "name", "") or "",
            "first_name": getattr(user, "first_name", "") or "",
            "last_name": getattr(user, "last_name", "") or "",
            "avatar": getattr(user, "avatar", "") or "",
            "bio": getattr(user, "bio", "") or "",
            "timezone": getattr(user, "timezone", "UTC") or "UTC",
            "notification_preferences": {},
            "auth_provider": getattr(user, "auth_provider", "email") or "email",
            "account_type": getattr(user, "account_type", "personal") or "personal",
            "primary_mode": getattr(user, "primary_mode", getattr(user, "account_type", "personal") or "personal"),
            "onboarding_completed": bool(getattr(user, "onboarding_completed", False)),
            "email_verified": bool(getattr(user, "email_verified", False)),
            "is_active": bool(getattr(user, "is_active", True)),
            "is_staff": bool(getattr(user, "is_staff", False)),
            "last_login": getattr(user, "last_login", None),
            "date_joined": getattr(user, "date_joined", None),
            "created_at": getattr(user, "created_at", None),
            "updated_at": getattr(user, "updated_at", None),
            "profile_completion": 0,
        }


def _frontend_url_with_path(path: str) -> str:
    frontend_url = _get_frontend_url().rstrip("/")
    if frontend_url:
        return f"{frontend_url}{path}"
    return path


def _normalize_frontend_next_path(next_path: str | None) -> str:
    candidate = str(next_path or "").strip()
    if not candidate.startswith("/"):
        return ""
    if candidate.startswith("//"):
        return ""
    return candidate


def build_auth_response_payload(*, user, token_payload: dict, refresh_cookie_set: bool = True) -> dict:
    return {
        "user": _serialize_authenticated_user(user),
        "tokens": {
            "access": token_payload["access"],
            "refresh": token_payload["refresh"],
            "refresh_expires_in": token_payload["refresh_expires_in"],
            "token_type": token_payload["token_type"],
            "refresh_cookie_set": refresh_cookie_set,
        },
    }


class RegisterView(APIView):
    permission_classes = [AuthEntryPointPermission]
    throttle_classes = [RegisterThrottle]

    @extend_schema(request=RegisterSerializer, responses=AuthTokenResponseSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = create_user_account(
            email=serializer.validated_data.get("email", ""),
            phone_number=serializer.validated_data.get("phone_number", ""),
            phone_country_code=serializer.validated_data.get("phone_country_code", ""),
            password=serializer.validated_data["password"],
            name=serializer.validated_data["name"],
            first_name=serializer.validated_data.get("first_name", ""),
            last_name=serializer.validated_data.get("last_name", ""),
            auth_provider=(
                User.AuthProvider.PHONE
                if serializer.validated_data.get("phone_number") and not serializer.validated_data.get("email")
                else User.AuthProvider.EMAIL
            ),
            account_type=serializer.validated_data.get("account_type", User.AccountType.PERSONAL),
            team_name=serializer.validated_data.get("team_name", ""),
        )
        token_payload = issue_tokens_for_user(user=user)
        register_auth_session(user=user, token_payload=token_payload, request=request)
        if not user.email_verified:
            send_email_verification(user=user)
        response = success_response(
            request=request,
            message="Registration completed successfully.",
            data=build_auth_response_payload(user=user, token_payload=token_payload, refresh_cookie_set=False),
            status_code=status.HTTP_201_CREATED,
        )
        response.data["data"]["tokens"]["refresh_cookie_set"] = try_set_refresh_cookie(response, token_payload["refresh"])
        return response


class LoginView(APIView):
    permission_classes = [AuthEntryPointPermission]
    throttle_classes = [LoginThrottle]

    @extend_schema(request=LoginSerializer, responses=AuthTokenResponseSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user, token_payload = authenticate_user_and_issue_tokens(
            credential=serializer.validated_data["credential"],
            password=serializer.validated_data["password"],
            request=request,
            account_type=serializer.validated_data.get("account_type", ""),
            remember_me=serializer.validated_data.get("remember_me", False),
        )
        response = success_response(
            request=request,
            message="Login successful.",
            data=build_auth_response_payload(user=user, token_payload=token_payload, refresh_cookie_set=False),
        )
        response.data["data"]["tokens"]["refresh_cookie_set"] = try_set_refresh_cookie(response, token_payload["refresh"])
        return response


class LogoutView(APIView):
    permission_classes = [AuthenticatedSessionPermission]

    @extend_schema(
        request=inline_serializer(
            name="LogoutRequest",
            fields={"refresh": serializers.CharField(required=False)},
        ),
        responses=None,
    )
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        refresh_token = normalize_token_value(request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME))
        if not refresh_token:
            refresh_token = normalize_token_value(request.data.get("refresh"))
        if refresh_token:
            revoke_auth_session_for_token(token_value=refresh_token)
            blacklist_refresh_token(refresh_token)

        response = success_response(
            request=request,
            message="Logout successful.",
            data=None,
            status_code=status.HTTP_205_RESET_CONTENT,
        )
        log_auth_action(
            actor=request.user,
            action=AuditAction.USER_LOGGED_OUT,
            target=request.user,
            metadata=build_audit_metadata(email=request.user.email),
        )
        clear_refresh_cookie(response)
        return response


class RefreshTokenView(APIView):
    permission_classes = [AuthEntryPointPermission]

    @extend_schema(request=RefreshTokenSerializer, responses=AuthTokenResponseSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_value = normalize_token_value(serializer.validated_data.get("refresh"))
        if not token_value:
            token_value = normalize_token_value(request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME))
        if not token_value:
            raise ValidationError({"refresh": _("Refresh token is required.")})

        try:
            session = ensure_auth_session_is_active(token_value=token_value)
            refresh = RefreshToken(token_value)
            user = User.objects.get(id=refresh["user_id"])
            token_payload = issue_tokens_for_user(user=user)
            blacklist_refresh_token(token_value)
        except (TokenError, User.DoesNotExist):
            raise ValidationError({"refresh": _("Refresh token is invalid or expired.")})
        except serializers.ValidationError as exc:
            raise ValidationError(exc.detail)
        rotate_auth_session(session=session, token_payload=token_payload, request=request)

        response = success_response(
            request=request,
            message="Token refreshed successfully.",
            data=build_auth_response_payload(user=user, token_payload=token_payload, refresh_cookie_set=False),
        )
        response.data["data"]["tokens"]["refresh_cookie_set"] = try_set_refresh_cookie(response, token_payload["refresh"])
        return response


class PasswordResetRequestView(APIView):
    permission_classes = [AuthEntryPointPermission]
    throttle_classes = [PasswordResetThrottle]

    @extend_schema(request=PasswordResetRequestSerializer, responses=None)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_password_reset(email=serializer.validated_data["email"], request=request)
        return success_response(
            request=request,
            message="If an account exists for that email, a reset link has been sent.",
            data=None,
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [AuthEntryPointPermission]
    throttle_classes = [PasswordResetThrottle]

    @extend_schema(request=PasswordResetConfirmSerializer, responses=None)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        confirm_password_reset(
            user=serializer.validated_data["user"],
            new_password=serializer.validated_data["new_password"],
        )
        return success_response(
            request=request,
            message="Password reset completed successfully.",
            data=None,
        )


class MeView(APIView):
    permission_classes = [AuthenticatedSessionPermission]

    @extend_schema(responses=CurrentUserSerializer)
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        return success_response(
            request=request,
            message="Authenticated user retrieved successfully.",
            data=CurrentUserSerializer(request.user).data,
        )


class EmailVerificationView(APIView):
    permission_classes = [AuthEntryPointPermission]

    @extend_schema(request=EmailVerificationRequestSerializer, responses=CurrentUserSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = EmailVerificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = verify_email_address(token=serializer.validated_data["token"])
        return success_response(
            request=request,
            message="Email verified successfully.",
            data=CurrentUserSerializer(user).data,
        )


class EmailVerificationResendView(APIView):
    permission_classes = [AuthenticatedSessionPermission]

    def post(self, request, *args, **kwargs):  # type: ignore[override]
        send_email_verification(user=request.user, actor=request.user)
        return success_response(
            request=request,
            message="Verification email queued successfully.",
            data={"email_verified": request.user.email_verified},
        )


class SessionListView(APIView):
    permission_classes = [AuthenticatedSessionPermission]

    @extend_schema(responses=AuthSessionSerializer(many=True))
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        return success_response(
            request=request,
            message="Sessions retrieved successfully.",
            data=AuthSessionSerializer(get_user_sessions(user=request.user), many=True).data,
        )


class SessionDetailView(APIView):
    permission_classes = [AuthenticatedSessionPermission]

    def delete(self, request, pk, *args, **kwargs):  # type: ignore[override]
        session = request.user.auth_sessions.filter(pk=pk).first()
        if session is None:
            return success_response(
                request=request,
                message="Session not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )
        revoke_auth_session(session=session)
        return success_response(
            request=request,
            message="Session revoked successfully.",
            data=None,
        )


class GoogleOAuthConfigView(APIView):
    permission_classes = [AuthEntryPointPermission]

    @extend_schema(responses=GoogleOAuthConfigSerializer)
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        config_payload = get_google_oauth_config(request=request)
        is_enabled = bool(config_payload.get("enabled"))
        next_path = _normalize_frontend_next_path(request.query_params.get("next"))
        account_type = str(request.query_params.get("account_type", "")).strip()
        flow = str(request.query_params.get("flow", "login")).strip() or "login"
        team_name = str(request.query_params.get("team_name", "")).strip()

        try:
            return success_response(
                request=request,
                message="Google OAuth configuration retrieved successfully.",
                data={
                    "provider": "google",
                    "enabled": is_enabled,
                    "login_url": (
                        build_google_login_url(
                            request,
                            next_path=next_path,
                            account_type=account_type,
                            flow=flow,
                            team_name=team_name,
                        )
                        if is_enabled
                        else None
                    ),
                    "callback_url": build_google_callback_url(request) if is_enabled else None,
                },
            )
        except Exception:
            logger.exception("Failed to build Google OAuth config payload")
            return success_response(
                request=request,
                message="Google OAuth configuration could not be built.",
                data={
                    "provider": "google",
                    "enabled": False,
                    "login_url": None,
                    "callback_url": None,
                },
                status_code=status.HTTP_200_OK,
            )


class GoogleLoginView(APIView):
    permission_classes = [AuthEntryPointPermission]

    @extend_schema(responses=GoogleOAuthLoginSerializer)
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        if not get_google_oauth_config(request=request).get("enabled"):
            raise ValidationError({"detail": "Google OAuth is not configured on the backend."})
        next_path = _normalize_frontend_next_path(request.query_params.get("next"))
        account_type = str(request.query_params.get("account_type", "")).strip()
        flow = str(request.query_params.get("flow", "login")).strip() or "login"
        team_name = str(request.query_params.get("team_name", "")).strip()
        valid_account_types = {choice for choice, _label in User.AccountType.choices}
        if flow == "register" and account_type not in valid_account_types:
            raise ValidationError({"account_type": "Choose your workspace mode before continuing with Google."})
        if flow == "login" and account_type not in valid_account_types:
            account_type = ""
        if flow not in {"login", "register"}:
            flow = "login"

        try:
            login_url = build_google_login_url(
                request,
                next_path=next_path,
                account_type=account_type,
                flow=flow,
                team_name=team_name,
            )
        except Exception as exc:
            logger.exception("Failed to generate Google login URL")
            raise ValidationError({"detail": f"Google OAuth configuration is invalid: {exc}"}) from exc
        if not login_url:
            raise ValidationError({"detail": "Google OAuth is not configured on the backend."})

        payload = {
            "provider": "google",
            "login_url": login_url,
        }

        if request.query_params.get("redirect", "true").lower() == "true":
            return HttpResponseRedirect(payload["login_url"])
        return success_response(
            request=request,
            message="Google login URL generated successfully.",
            data=payload,
        )


class GoogleOAuthCallbackView(APIView):
    permission_classes = [AuthEntryPointPermission]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        error = request.query_params.get("error")
        if error:
            redirect_url = _frontend_url_with_path("/login?error=google_auth_failed")
            return HttpResponseRedirect(redirect_url)

        code = request.query_params.get("code")

        if not code:
            redirect_url = _frontend_url_with_path("/login?error=no_authorization_code")
            return HttpResponseRedirect(redirect_url)

        from apps.authentication.adapter import handle_google_oauth_callback
        return handle_google_oauth_callback(request)


class GoogleAuthView(APIView):
    """
    POST /api/v1/auth/google/
    
    Receive Google ID token from frontend, verify it, and issue JWT tokens.
    """
    permission_classes = [AuthEntryPointPermission]
    throttle_classes = [LoginThrottle]

    def post(self, request, *args, **kwargs):  # type: ignore[override]
        from rest_framework import status as rf_status
        
        from apps.authentication.serializers import (
            GoogleAuthRequestSerializer,
            GoogleAuthResponseSerializer,
        )
        from apps.authentication.google_service import (
            authenticate_google_user,
            GoogleAuthError,
            AccountConflictError,
        )
        
        serializer = GoogleAuthRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        credential = serializer.validated_data["credential"]
        account_type = serializer.validated_data["account_type"]
        team_name = serializer.validated_data.get("team_name", "")

        try:
            result = authenticate_google_user(credential, account_type=account_type, team_name=team_name)
            
            user = result["user"]
            tokens = result["tokens"]
            is_new_user = result["is_new_user"]

            register_auth_session(user=user, token_payload=tokens, request=request)
            response = success_response(
                request=request,
                message="Google authentication successful",
                data={
                    **build_auth_response_payload(user=user, token_payload=tokens, refresh_cookie_set=False),
                    "is_new_user": is_new_user,
                },
            )
            response.data["data"]["tokens"]["refresh_cookie_set"] = try_set_refresh_cookie(response, tokens["refresh"])
            return response
            
        except AccountConflictError as e:
            return error_response(
                request=request,
                message="Account conflict detected",
                errors={"account": [e.message]},
                status_code=rf_status.HTTP_409_CONFLICT,
            )
        
        except GoogleAuthError as e:
            return error_response(
                request=request,
                message="Google authentication failed",
                errors={"google": [e.message]},
                status_code=rf_status.HTTP_400_BAD_REQUEST,
            )
        
        except Exception as e:
            logger.exception("Unexpected error in Google auth")
            return error_response(
                request=request,
                message="Google authentication is temporarily unavailable",
                errors={
                    "google": [
                        "Google sign-in could not be completed right now. Please try again or use email and password."
                    ]
                },
                status_code=rf_status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
