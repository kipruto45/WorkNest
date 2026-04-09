from __future__ import annotations

from django.conf import settings

from apps.integrations.constants import (
    EMAIL_PROVIDER_SENDGRID,
    EMAIL_PROVIDER_SMTP,
    SMS_PROVIDER_AFRICAS_TALKING,
    SMS_PROVIDER_CELCOM,
    STORAGE_PROVIDER_LOCAL,
    STORAGE_PROVIDER_SUPABASE,
)
from apps.integrations.exceptions import IntegrationConfigurationError, OAuthValidationFailedError
from apps.integrations.email.services import (
    get_email_provider,
    send_notification_email,
    send_password_reset_email,
    send_system_email,
    send_team_invite_email,
)
from apps.integrations.sms.services import get_sms_provider
from apps.integrations.oauth.services import (
    get_google_oauth_config,
    get_google_oauth_service,
    handle_google_auth_request,
    verify_google_identity,
)
from apps.integrations.storage.services import (
    delete_file_from_storage,
    generate_private_file_url,
    get_storage_provider,
    open_storage_file,
    upload_file_to_storage,
)
from apps.integrations.supabase.client import SupabaseClient
from apps.integrations.supabase.storage import SupabaseStorageClient
from apps.integrations.validators import ensure_required_settings


def validate_integrations_configuration() -> dict:
    email_provider = get_email_provider().provider_name
    sms_provider = get_sms_provider().provider_name if getattr(settings, "SMS_ENABLED", False) else ""
    storage_provider = get_storage_provider().provider_name
    google_service = get_google_oauth_service()
    google_enabled = google_service.is_enabled()

    if email_provider == EMAIL_PROVIDER_SENDGRID:
        ensure_required_settings(setting_names=["SENDGRID_API_KEY", "DEFAULT_FROM_EMAIL"])
    elif email_provider == EMAIL_PROVIDER_SMTP:
        ensure_required_settings(setting_names=["DEFAULT_FROM_EMAIL"])

    if sms_provider == SMS_PROVIDER_AFRICAS_TALKING:
        ensure_required_settings(setting_names=["AFRICAS_TALKING_USERNAME", "AFRICAS_TALKING_API_KEY"])
    elif sms_provider == SMS_PROVIDER_CELCOM:
        ensure_required_settings(setting_names=["CELCOM_PARTNER_ID", "CELCOM_API_KEY", "CELCOM_SHORTCODE"])

    if storage_provider == STORAGE_PROVIDER_SUPABASE:
        ensure_required_settings(setting_names=["SUPABASE_URL", "ATTACHMENTS_SUPABASE_BUCKET"])
        if not getattr(settings, "SUPABASE_KEY", "") and not getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", ""):
            raise IntegrationConfigurationError(
                "Supabase storage requires SUPABASE_KEY or SUPABASE_SERVICE_ROLE_KEY."
            )
    elif storage_provider == STORAGE_PROVIDER_LOCAL:
        ensure_required_settings(setting_names=["MEDIA_URL"])

    if any((google_service.client_id, google_service.client_secret)):
        try:
            google_service.validate_configuration()
        except OAuthValidationFailedError as exc:
            raise IntegrationConfigurationError(str(exc)) from exc

    return {
        "email_provider": email_provider,
        "sms_provider": sms_provider,
        "storage_provider": storage_provider,
        "google_oauth_enabled": google_enabled,
    }


def get_supabase_client(*, base_url: str | None = None, api_key: str | None = None, timeout: int | None = None) -> SupabaseClient:
    return SupabaseClient(base_url=base_url, api_key=api_key, timeout=timeout)


def get_supabase_storage_client(*, client: SupabaseClient | None = None) -> SupabaseStorageClient:
    return SupabaseStorageClient(client=client)
