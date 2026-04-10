"""
Google OAuth2 Authentication Service

Handles verification of Google ID tokens and user creation/login.
"""
from __future__ import annotations

import logging

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string

from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, log_auth_action
from apps.authentication.services import create_user_account, issue_tokens_for_user, sync_google_account_profile
from apps.memberships.models import Membership
from apps.users.models import User as UserModel

User = get_user_model()

logger = logging.getLogger(__name__)


class GoogleAuthError(Exception):
    """Custom exception for Google auth errors."""
    def __init__(self, message: str, error_code: str = "google_auth_error"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class AccountConflictError(GoogleAuthError):
    """Raised when account conflict is detected."""
    def __init__(self, message: str):
        super().__init__(message, "account_conflict")


class AccountTypeMismatchError(GoogleAuthError):
    """Raised when the selected account type does not match the stored account type."""
    def __init__(self, message: str = "Selected workspace mode does not match this account."):
        super().__init__(message, "account_type_mismatch")


def _matches_requested_account_type(*, user: UserModel, account_type: str) -> bool:
    if user.account_type == account_type:
        return True

    if account_type == UserModel.AccountType.PERSONAL:
        return Membership.objects.filter(
            user=user,
            status=Membership.Status.ACTIVE,
            team__is_archived=False,
            team__is_personal=True,
        ).exists()

    if account_type == UserModel.AccountType.TEAM:
        return Membership.objects.filter(
            user=user,
            status=Membership.Status.ACTIVE,
            team__is_archived=False,
            team__is_personal=False,
        ).exists()

    return False


def verify_google_token(google_credential: str) -> dict:
    """
    Verify a Google ID token and extract user info.
    
    Uses Google's tokeninfo endpoint for ID token verification.
    Falls back to parsing JWT if needed.
    """
    client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', '')
    
    if not client_id:
        raise GoogleAuthError("Google OAuth is not configured", "not_configured")
    
    try:
        verify_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={google_credential}"
        response = requests.get(verify_url, timeout=30)
        
        if response.status_code != 200:
            logger.warning(f"Google token verification failed: {response.status_code}")
            raise GoogleAuthError("Invalid Google token", "invalid_token")
        
        data = response.json()
        
        if 'aud' in data and data['aud'] != client_id:
            raise GoogleAuthError("Token audience mismatch", "invalid_token")
        
        if 'email' not in data:
            raise GoogleAuthError("No email in Google token", "no_email")
        
        return {
            'email': data['email'].lower().strip(),
            'email_verified': data.get('email_verified', False),
            'name': data.get('name', ''),
            'first_name': data.get('given_name', ''),
            'last_name': data.get('family_name', ''),
            'avatar': data.get('picture', ''),
            ' google_sub': data.get('sub', ''),
        }
        
    except requests.RequestException as e:
        logger.error(f"Google token verification request failed: {e}")
        raise GoogleAuthError("Unable to verify Google token", "verification_failed")


def get_or_create_google_user(
    google_user_info: dict,
    *,
    account_type: str,
    team_name: str = "",
    create_if_not_exists: bool = True,
) -> tuple[UserModel, bool]:
    """
    Find or create user based on Google identity.
    
    Returns (user, is_new_user) tuple.
    
    Account linking rules:
    - Case A: New user -> create account
    - Case B: Existing Google user -> return existing
    - Case C: Email/password user with same email -> link if verified
    - Case D: Conflicting state -> raise error
    """
    email = google_user_info['email']
    try:
        existing_user = User.objects.get(email__iexact=email)
        if not _matches_requested_account_type(user=existing_user, account_type=account_type):
            raise AccountTypeMismatchError()
        
        if existing_user.auth_provider == UserModel.AuthProvider.GOOGLE:
            sync_google_account_profile(
                user=existing_user,
                name=google_user_info.get('name', ''),
                first_name=google_user_info.get('first_name', ''),
                last_name=google_user_info.get('last_name', ''),
                avatar=google_user_info.get('avatar', ''),
                email_verified=google_user_info.get('email_verified', False),
            )
            return existing_user, False
        
        if existing_user.auth_provider == UserModel.AuthProvider.EMAIL:
            if google_user_info.get('email_verified', False):
                sync_google_account_profile(
                    user=existing_user,
                    name=google_user_info.get('name', ''),
                    first_name=google_user_info.get('first_name', ''),
                    last_name=google_user_info.get('last_name', ''),
                    avatar=google_user_info.get('avatar', ''),
                    email_verified=True,
                    overwrite_profile=True,
                )
                
                log_auth_action(
                    actor=existing_user,
                    action=AuditAction.ACCOUNT_LINKED,
                    target=existing_user,
                    metadata=build_audit_metadata(
                        email=email,
                        auth_provider='google',
                        linked_from='email'
                    ),
                )
                
                return existing_user, False
            
            raise AccountConflictError(
                "An account with this email already exists. "
                "Please sign in with your password first, then link Google "
                "from your account settings."
            )
        
        raise AccountConflictError(
            "This account uses a different authentication method. "
            "Please contact support."
        )
        
    except User.DoesNotExist:
        if not create_if_not_exists:
            return None, True
        
        name = google_user_info.get('name', '')
        first_name = google_user_info.get('first_name', '')
        last_name = google_user_info.get('last_name', '')
        
        new_user = create_user_account(
            email=email,
            password=get_random_string(32),
            name=name or first_name or email.split('@')[0],
            first_name=first_name,
            last_name=last_name,
            auth_provider=UserModel.AuthProvider.GOOGLE,
            account_type=account_type,
            team_name=team_name,
        )
        sync_google_account_profile(
            user=new_user,
            name=name or first_name or email.split('@')[0],
            first_name=first_name,
            last_name=last_name,
            avatar=google_user_info.get('avatar', ''),
            email_verified=google_user_info.get('email_verified', False),
        )
        
        log_auth_action(
            actor=new_user,
            action=AuditAction.USER_REGISTERED,
            target=new_user,
            metadata=build_audit_metadata(
                email=email,
                auth_provider=UserModel.AuthProvider.GOOGLE,
            ),
        )
        
        return new_user, True


def authenticate_google_user(google_credential: str, *, account_type: str, team_name: str = "") -> dict:
    """
    Main entry point for Google authentication.
    
    Verifies the Google token, creates/finds user, and returns auth payload.
    """
    google_user_info = verify_google_token(google_credential)
    
    user, is_new = get_or_create_google_user(google_user_info, account_type=account_type, team_name=team_name)
    
    log_auth_action(
        actor=user,
        action=AuditAction.USER_LOGGED_IN,
        target=user,
        metadata=build_audit_metadata(
            email=user.email,
            auth_provider=UserModel.AuthProvider.GOOGLE,
        ),
    )
    
    token_payload = issue_tokens_for_user(user=user)
    
    return {
        'user': user,
        'tokens': token_payload,
        'is_new_user': is_new,
    }


def validate_google_credential(google_credential: str) -> dict:
    """
    Validate a Google credential without creating user.
    
    Used for account linking flow.
    """
    return verify_google_token(google_credential)
