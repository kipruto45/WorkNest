from __future__ import annotations

import json
import secrets
import urllib.parse
from typing import Any
from urllib.parse import urlencode

from django.http import HttpResponseRedirect, HttpRequest
from django.contrib.auth import get_user_model
from django.conf import settings

from apps.authentication.services import create_user_account, issue_tokens_for_user
from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, log_auth_action
from apps.users.models import User as UserModel

User = get_user_model()


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
    response.raise_for_status()
    return response.json()


def get_google_user_info(access_token: str) -> dict:
    """Get user info from Google using access token."""
    import requests
    
    userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
    headers = {'Authorization': f'Bearer {access_token}'}
    
    response = requests.get(userinfo_url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def find_or_create_google_user(email: str, first_name: str = "", last_name: str = "", name: str = "") -> UserModel:
    """Find existing user or create new one for Google auth."""
    try:
        user = User.objects.get(email__iexact=email)
        
        if user.auth_provider != UserModel.AuthProvider.GOOGLE:
            user.auth_provider = UserModel.AuthProvider.GOOGLE
            user.email_verified = True
            user.save(update_fields=['auth_provider', 'email_verified', 'updated_at'])
        
        return user
        
    except User.DoesNotExist:
        full_name = name or f"{first_name} {last_name}".strip() or email.split('@')[0]
        return create_user_account(
            email=email,
            password=User.objects.make_random_password(),
            name=full_name,
            first_name=first_name,
            last_name=last_name,
            auth_provider=UserModel.AuthProvider.GOOGLE,
        )


def handle_google_oauth_callback(request: HttpRequest) -> HttpResponseRedirect:
    """Process the Google OAuth callback and redirect with tokens."""
    error = request.GET.get("error")
    if error:
        redirect_url = f"{settings.FRONTEND_URL.rstrip('/')}/login?error=google_auth_failed"
        return HttpResponseRedirect(redirect_url)
    
    code = request.GET.get("code")
    if not code:
        redirect_url = f"{settings.FRONTEND_URL.rstrip('/')}/login?error=no_authorization_code"
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
            redirect_url = f"{settings.FRONTEND_URL.rstrip('/')}/login?error=no_access_token"
            return HttpResponseRedirect(redirect_url)
        
        user_info = get_google_user_info(access_token)
        
        email = user_info.get('email', '').strip().lower()
        first_name = user_info.get('given_name', '')
        last_name = user_info.get('family_name', '')
        name = user_info.get('name', '')
        
        if not email:
            redirect_url = f"{settings.FRONTEND_URL.rstrip('/')}/login?error=no_email"
            return HttpResponseRedirect(redirect_url)
        
        user = find_or_create_google_user(email, first_name, last_name, name)
        
        log_auth_action(
            action=AuditAction.USER_LOGGED_IN,
            actor=user,
            target=user,
            metadata=build_audit_metadata(email=user.email, auth_provider=UserModel.AuthProvider.GOOGLE),
        )
        
        token_payload = issue_tokens_for_user(user=user)
        
        frontend_url = f"{settings.FRONTEND_URL.rstrip('/')}/auth/google/callback"
        user_payload = json.dumps(
            {
                "id": str(user.id),
                "email": user.email,
                "name": user.name,
                "avatar": user.avatar or "",
                "first_name": user.first_name,
                "last_name": user.last_name,
            },
            separators=(",", ":"),
        )
        params = urlencode(
            {
                "access": token_payload["access"],
                "refresh": token_payload["refresh"],
                "user": user_payload,
            }
        )
        
        return HttpResponseRedirect(f"{frontend_url}?{params}")
        
    except Exception:
        redirect_url = f"{settings.FRONTEND_URL.rstrip('/')}/login?error=google_auth_failed"
        return HttpResponseRedirect(redirect_url)
