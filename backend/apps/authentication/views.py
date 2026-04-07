from __future__ import annotations

import logging
from urllib.parse import urlencode
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
from apps.authentication.serializers import (
    AuthTokenResponseSerializer,
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
    get_google_oauth_config,
    handle_google_auth,
    issue_tokens_for_user,
    normalize_token_value,
    request_password_reset,
    set_refresh_cookie,
)
from apps.authentication.throttles import LoginThrottle, PasswordResetThrottle, RegisterThrottle
from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, log_auth_action
from apps.common.responses import success_response
from apps.users.serializers import CurrentUserSerializer

User = get_user_model()


def build_auth_response_payload(*, user, token_payload: dict) -> dict:
    return {
        "user": CurrentUserSerializer(user).data,
        "tokens": {
            "access": token_payload["access"],
            "refresh": token_payload["refresh"],
            "refresh_expires_in": token_payload["refresh_expires_in"],
            "token_type": token_payload["token_type"],
            "refresh_cookie_set": True,
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
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            name=serializer.validated_data["name"],
            first_name=serializer.validated_data.get("first_name", ""),
            last_name=serializer.validated_data.get("last_name", ""),
        )
        token_payload = issue_tokens_for_user(user=user)
        response = success_response(
            request=request,
            message="Registration completed successfully.",
            data=build_auth_response_payload(user=user, token_payload=token_payload),
            status_code=status.HTTP_201_CREATED,
        )
        set_refresh_cookie(response, token_payload["refresh"])
        return response


class LoginView(APIView):
    permission_classes = [AuthEntryPointPermission]
    throttle_classes = [LoginThrottle]

    @extend_schema(request=LoginSerializer, responses=AuthTokenResponseSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user, token_payload = authenticate_user_and_issue_tokens(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            request=request,
            remember_me=serializer.validated_data.get("remember_me", False),
        )
        response = success_response(
            request=request,
            message="Login successful.",
            data=build_auth_response_payload(user=user, token_payload=token_payload),
        )
        set_refresh_cookie(response, token_payload["refresh"])
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
            refresh = RefreshToken(token_value)
            user = User.objects.get(id=refresh["user_id"])
            token_payload = issue_tokens_for_user(user=user)
            blacklist_refresh_token(token_value)
        except (TokenError, User.DoesNotExist):
            raise ValidationError({"refresh": _("Refresh token is invalid or expired.")})

        response = success_response(
            request=request,
            message="Token refreshed successfully.",
            data=build_auth_response_payload(user=user, token_payload=token_payload),
        )
        set_refresh_cookie(response, token_payload["refresh"])
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


class GoogleOAuthConfigView(APIView):
    permission_classes = [AuthEntryPointPermission]

    @staticmethod
    def _build_callback_url(request) -> str:
        configured_redirect_uri = str(getattr(settings, "GOOGLE_REDIRECT_URI", "")).strip()
        if configured_redirect_uri:
            return configured_redirect_uri
        backend_url = str(getattr(settings, "BACKEND_URL", "")).strip().rstrip("/")
        if not backend_url:
            backend_url = request.build_absolute_uri("/").rstrip("/")
        return f"{backend_url}/api/v1/auth/google/callback/"

    @classmethod
    def _build_login_url(cls, request) -> str:
        client_id = str(getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")).strip()
        callback_url = cls._build_callback_url(request)
        params = {
            "client_id": client_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "online",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    @extend_schema(responses=GoogleOAuthConfigSerializer)
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        client_id = str(getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")).strip()
        client_secret = str(getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")).strip()
        is_enabled = bool(client_id and client_secret)

        try:
            return success_response(
                request=request,
                message="Google OAuth configuration retrieved successfully.",
                data={
                    "provider": "google",
                    "enabled": is_enabled,
                    "login_url": self._build_login_url(request) if is_enabled else None,
                    "callback_url": self._build_callback_url(request) if is_enabled else None,
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
        client_id = str(getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")).strip()
        client_secret = str(getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")).strip()
        if not client_id or not client_secret:
            raise ValidationError({"detail": "Google OAuth is not configured on the backend."})

        try:
            payload = {
                "provider": "google",
                "login_url": GoogleOAuthConfigView._build_login_url(request),
            }
        except Exception as exc:
            logger.exception("Failed to generate Google login URL")
            raise ValidationError({"detail": f"Google OAuth configuration is invalid: {exc}"}) from exc

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
        from django.conf import settings
        
        error = request.query_params.get("error")
        if error:
            redirect_url = f"{settings.FRONTEND_URL.rstrip('/')}/login?error=google_auth_failed"
            return HttpResponseRedirect(redirect_url)
        
        code = request.query_params.get("code")
        state = request.query_params.get("state")
        
        if not code:
            redirect_url = f"{settings.FRONTEND_URL.rstrip('/')}/login?error=no_authorization_code"
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
        
        try:
            result = authenticate_google_user(credential)
            
            user = result["user"]
            tokens = result["tokens"]
            is_new_user = result["is_new_user"]
            
            return success_response(
                request=request,
                message="Google authentication successful",
                data={
                    "user": {
                        "id": str(user.id),
                        "email": user.email,
                        "name": user.name,
                        "avatar": user.avatar or "",
                    },
                    "tokens": tokens,
                    "is_new_user": is_new_user,
                },
            )
            
        except AccountConflictError as e:
            return success_response(
                request=request,
                message="Account conflict detected",
                data=None,
                errors={"account": [e.message]},
                status_code=rf_status.HTTP_409_CONFLICT,
            )
        
        except GoogleAuthError as e:
            return success_response(
                request=request,
                message="Google authentication failed",
                data=None,
                errors={"google": [e.message]},
                status_code=rf_status.HTTP_400_BAD_REQUEST,
            )
        
        except Exception as e:
            logger.exception("Unexpected error in Google auth")
            return success_response(
                request=request,
                message="Google authentication could not be completed",
                data=None,
                errors={"error": ["An unexpected error occurred. Please try again."]},
                status_code=rf_status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
