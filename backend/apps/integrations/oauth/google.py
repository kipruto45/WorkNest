from __future__ import annotations

from urllib.parse import urlencode

from django.conf import settings

from apps.integrations.constants import OAUTH_PROVIDER_GOOGLE
from apps.integrations.exceptions import OAuthValidationFailedError


class GoogleOAuthProvider:
    name = OAUTH_PROVIDER_GOOGLE

    def __init__(self, *, client_id: str | None = None, client_secret: str | None = None) -> None:
        self.client_id = client_id if client_id is not None else getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")
        self.client_secret = (
            client_secret if client_secret is not None else getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")
        )

    def is_enabled(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def validate_configuration(self) -> None:
        if self.client_id and self.client_secret:
            return
        if not self.client_id and not self.client_secret:
            raise OAuthValidationFailedError("Google OAuth is not configured.")
        raise OAuthValidationFailedError("Google OAuth configuration is incomplete.")

    def _resolve_backend_base_url(self, request) -> str:
        configured_base = str(getattr(settings, "BACKEND_URL", "")).strip().rstrip("/")
        if configured_base:
            return configured_base
        return request.build_absolute_uri("/").rstrip("/")

    def build_login_url(self, request) -> str:
        callback_url = self.build_callback_url(request)
        params = {
            "client_id": self.client_id,
            "redirect_uri": callback_url,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "online",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    def build_callback_url(self, request) -> str:
        configured_callback = str(getattr(settings, "GOOGLE_REDIRECT_URI", "")).strip()
        if configured_callback:
            return configured_callback
        base = self._resolve_backend_base_url(request)
        return f"{base}/api/v1/auth/google/callback/"

    def build_config_payload(self, request) -> dict:
        is_enabled = self.is_enabled()
        return {
            "provider": self.name,
            "enabled": is_enabled,
            "login_url": self.build_login_url(request) if is_enabled else None,
            "callback_url": self.build_callback_url(request) if is_enabled else None,
        }

    def build_login_payload(self, request) -> dict:
        self.validate_configuration()
        return {
            "provider": self.name,
            "login_url": self.build_login_url(request),
        }

    def normalize_identity(self, payload: dict) -> dict:
        email = str(payload.get("email", "")).strip().lower()
        subject = str(payload.get("sub", "")).strip()
        if not email or not subject:
            raise OAuthValidationFailedError("Google identity payload is invalid.")
        return {
            "provider": self.name,
            "provider_user_id": subject,
            "email": email,
            "email_verified": bool(payload.get("email_verified", False)),
            "name": str(payload.get("name", "")).strip(),
            "first_name": str(payload.get("given_name", "")).strip(),
            "last_name": str(payload.get("family_name", "")).strip(),
            "avatar": str(payload.get("picture", "")).strip(),
        }
