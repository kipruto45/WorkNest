from __future__ import annotations

from pathlib import PurePosixPath

from django.conf import settings

from apps.integrations.exceptions import IntegrationConfigurationError, IntegrationValidationError


def validate_provider_name(*, provider_name: str, supported_providers: set[str], provider_kind: str) -> str:
    normalized = str(provider_name).strip().lower()
    if normalized not in supported_providers:
        supported = ", ".join(sorted(supported_providers))
        raise IntegrationConfigurationError(f"Unsupported {provider_kind} provider '{provider_name}'. Supported: {supported}.")
    return normalized


def ensure_required_settings(*, setting_names: list[str]) -> None:
    missing = [name for name in setting_names if not getattr(settings, name, None)]
    if missing:
        raise IntegrationConfigurationError(f"Missing required integration settings: {', '.join(sorted(missing))}.")


def validate_email_recipients(recipients) -> list[str]:
    if isinstance(recipients, str):
        recipients = [recipients]
    normalized = [str(value).strip() for value in (recipients or []) if str(value).strip()]
    if not normalized:
        raise IntegrationValidationError("At least one email recipient is required.")
    return normalized


def validate_email_subject(subject: str) -> str:
    value = str(subject).strip()
    if not value:
        raise IntegrationValidationError("Email subject is required.")
    return value


def validate_storage_path(file_path: str) -> str:
    raw_path = str(file_path or "").strip().replace("\\", "/")
    if not raw_path:
        raise IntegrationValidationError("A storage file path is required.")

    path = PurePosixPath(raw_path)
    if path.is_absolute() or ".." in path.parts:
        raise IntegrationValidationError("Unsafe storage file path provided.")

    normalized = path.as_posix().lstrip("/")
    if normalized in {"", "."}:
        raise IntegrationValidationError("Unsafe storage file path provided.")
    return normalized


def sanitize_provider_error(exc: Exception, *, fallback_message: str) -> str:
    message = str(exc).strip()
    if not message:
        return fallback_message
    lowered = message.lower()
    sensitive_markers = ("key", "secret", "token", "authorization", "apikey", "password")
    if any(marker in lowered for marker in sensitive_markers):
        return fallback_message
    return message
