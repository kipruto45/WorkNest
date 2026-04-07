from __future__ import annotations

import json
import logging
from urllib.parse import urlencode

from django.http import HttpResponseRedirect, HttpRequest
from django.contrib.auth import get_user_model
from django.conf import settings

from apps.authentication.services import create_user_account, issue_tokens_for_user, sync_google_account_profile
from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, log_auth_action
from apps.integrations.email.builders import _get_frontend_url
from apps.users.serializers import CurrentUserSerializer
from apps.users.models import User as UserModel

User = get_user_model()
logger = logging.getLogger(__name__)


class GoogleOAuthCallbackError(Exception):
    def __init__(self, error_code: str, message: str):
        self.error_code = error_code
        super().__init__(message)


def _frontend_url_with_path(path: str) -> str:
    frontend_url = _get_frontend_url().rstrip("/")
    if frontend_url:
        return f"{frontend_url}{path}"
    return path


def get_google_authorization_url(redirect_uri: str, state: str = "") -> str:
    """Build the Google OAuth authorization URL."""
    client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')
    params = {
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'access_type': 'online',
        'state': state,
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def exchange_code_for_token(code: str, redirect_uri: str) -> dict:
    """Exchange authorization code for access token using Google's OAuth2."""
    import requests
    
    client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')
    client_secret = getattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET', '')
    
    token_url = 'https://oauth2.googleapis.com/token'
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': redirect_uri,
    }
    
    response = requests.post(token_url, data=data, timeout=30)
    if response.status_code >= 400:
        try:
            error_payload = response.json()
        except ValueError:
            error_payload = {"detail": response.text}
        logger.warning("Google token exchange failed", extra={"google_error_payload": error_payload})
        raise GoogleOAuthCallbackError(
            "google_token_exchange_failed",
            str(error_payload.get("error_description") or error_payload.get("error") or "Google token exchange failed."),
        )
    return response.json()


def get_google_user_info(access_token: str) -> dict:
    """Get user info from Google using access token."""
    import requests
    
    userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.get(userinfo_url, headers=headers, timeout=30)
    if response.status_code >= 400:
        try:
            error_payload = response.json()
        except ValueError:
            error_payload = {"detail": response.text}
        logger.warning("Google userinfo request failed", extra={"google_error_payload": error_payload})
        raise GoogleOAuthCallbackError(
            "google_userinfo_failed",
            str(error_payload.get("error", {}).get("message") or error_payload.get("error") or "Google profile lookup failed."),
        )
    return response.json()


def find_or_create_google_user(
    email: str,
    first_name: str = "",
    last_name: str = "",
    name: str = "",
    avatar: str = "",
) -> UserModel:
    """Find existing user or create new one for Google auth."""
    try:
        user = User.objects.get(email__iexact=email)

        return sync_google_account_profile(
            user=user,
            name=name,
            first_name=first_name,
            last_name=last_name,
            avatar=avatar,
            email_verified=True,
        )

    except User.DoesNotExist:
        full_name = name or f"{first_name} {last_name}".strip() or email.split('@')[0]
        user = create_user_account(
            email=email,
            password=User.objects.make_random_password(),
            name=full_name,
            first_name=first_name,
            last_name=last_name,
            auth_provider=UserModel.AuthProvider.GOOGLE,
        )
        return sync_google_account_profile(
            user=user,
            name=full_name,
            first_name=first_name,
            last_name=last_name,
            avatar=avatar,
            email_verified=True,
        )


def handle_google_oauth_callback(request: HttpRequest) -> HttpResponseRedirect:
    """Process the Google OAuth callback and redirect with tokens."""
    error = request.GET.get("error")
    if error:
        redirect_url = _frontend_url_with_path("/login?error=google_auth_failed")
        return HttpResponseRedirect(redirect_url)
    
    code = request.GET.get("code")
    if not code:
        redirect_url = _frontend_url_with_path("/login?error=no_authorization_code")
        return HttpResponseRedirect(redirect_url)
    
    try:
        configured_redirect_uri = str(getattr(settings, "GOOGLE_REDIRECT_URI", "")).strip()
        if configured_redirect_uri:
            redirect_uri = configured_redirect_uri
        else:
            backend_url = str(getattr(settings, "BACKEND_URL", "")).strip().rstrip("/")
            if not backend_url:
                backend_url = request.build_absolute_uri("/").rstrip("/")
            redirect_uri = f"{backend_url}/api/v1/auth/google/callback/"
        
        token_data = exchange_code_for_token(code, redirect_uri)
        access_token = token_data.get('access_token')
        
        if not access_token:
            redirect_url = _frontend_url_with_path("/login?error=no_access_token")
            return HttpResponseRedirect(redirect_url)
        
        user_info = get_google_user_info(access_token)
        
        email = user_info.get('email', '').strip().lower()
        first_name = user_info.get('given_name', '')
        last_name = user_info.get('family_name', '')
        name = user_info.get('name', '')
        avatar = user_info.get('picture', '')
        
        if not email:
            redirect_url = _frontend_url_with_path("/login?error=no_email")
            return HttpResponseRedirect(redirect_url)
        
        user = find_or_create_google_user(email, first_name, last_name, name, avatar)
        
        log_auth_action(
            action=AuditAction.USER_LOGGED_IN,
            actor=user,
            target=user,
            metadata=build_audit_metadata(email=user.email, auth_provider=UserModel.AuthProvider.GOOGLE),
        )
        
        token_payload = issue_tokens_for_user(user=user)
        
        frontend_url = _frontend_url_with_path("/auth/google/callback")
        user_payload = json.dumps(CurrentUserSerializer(user).data, separators=(",", ":"))
        params = urlencode(
            {
                "access": token_payload["access"],
                "refresh": token_payload["refresh"],
                "user": user_payload,
            }
        )
        
        return HttpResponseRedirect(f"{frontend_url}?{params}")
        
    except GoogleOAuthCallbackError as exc:
        logger.warning("Google OAuth callback failed: %s", exc)
        redirect_url = _frontend_url_with_path(f"/login?error={exc.error_code}")
        return HttpResponseRedirect(redirect_url)
    except Exception:
        logger.exception("Unhandled Google OAuth callback failure")
        redirect_url = _frontend_url_with_path("/login?error=google_auth_failed")
        return HttpResponseRedirect(redirect_url)
