from __future__ import annotations

from apps.integrations.oauth.google import GoogleOAuthProvider


def get_google_oauth_service() -> GoogleOAuthProvider:
    return GoogleOAuthProvider()


def get_google_oauth_config(*, request) -> dict:
    return get_google_oauth_service().build_config_payload(request)


def handle_google_auth_request(*, request) -> dict:
    return get_google_oauth_service().build_login_payload(request)


def verify_google_identity(*, payload: dict) -> dict:
    return get_google_oauth_service().normalize_identity(payload)
