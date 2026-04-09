from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from apps.integrations.constants import (
    AFRICAS_TALKING_LIVE_BASE_URL,
    AFRICAS_TALKING_SANDBOX_BASE_URL,
    AFRICAS_TALKING_SANDBOX_USERNAME,
    CELCOM_SMS_BASE_URL,
    SMS_PROVIDER_AFRICAS_TALKING,
    SMS_PROVIDER_CELCOM,
)
from apps.integrations.sms.exceptions import SMSConfigurationError

TRUE_VALUES = {"1", "true", "yes", "on"}
FALSE_VALUES = {"0", "false", "no", "off"}
SANDBOX_ENVIRONMENT = "sandbox"
LIVE_ENVIRONMENT = "live"


def _mask_value(value: str, *, prefix: int = 3, suffix: int = 2) -> str:
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""
    if len(raw_value) <= prefix + suffix:
        return "*" * len(raw_value)
    return f"{raw_value[:prefix]}{'*' * (len(raw_value) - prefix - suffix)}{raw_value[-suffix:]}"


def _parse_optional_bool(value, *, setting_name: str) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized == "":
        return None
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise SMSConfigurationError(f"{setting_name} must be a boolean value.")


def _normalize_environment(value) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"", SANDBOX_ENVIRONMENT, "test", "testing"}:
        return SANDBOX_ENVIRONMENT
    if normalized in {LIVE_ENVIRONMENT, "production", "prod"}:
        return LIVE_ENVIRONMENT
    raise SMSConfigurationError("AFRICAS_TALKING_ENVIRONMENT must be either 'sandbox' or 'live'.")


def _resolve_use_sandbox(*, environment: str) -> bool:
    legacy_flag = _parse_optional_bool(getattr(settings, "SMS_USE_SANDBOX", None), setting_name="SMS_USE_SANDBOX")
    provider_flag = _parse_optional_bool(
        getattr(settings, "AFRICAS_TALKING_USE_SANDBOX", None),
        setting_name="AFRICAS_TALKING_USE_SANDBOX",
    )

    if legacy_flag is not None and provider_flag is not None and legacy_flag != provider_flag:
        raise SMSConfigurationError("SMS_USE_SANDBOX and AFRICAS_TALKING_USE_SANDBOX must match when both are set.")

    configured_flag = provider_flag if provider_flag is not None else legacy_flag
    expected_flag = environment == SANDBOX_ENVIRONMENT
    if configured_flag is not None and configured_flag != expected_flag:
        raise SMSConfigurationError(
            "AFRICAS_TALKING_ENVIRONMENT and sandbox flags disagree. Use sandbox/true for testing or live/false for production."
        )
    return expected_flag


@dataclass(frozen=True, slots=True)
class AfricasTalkingConfig:
    provider: str
    username: str
    api_key: str
    sender_id: str
    environment: str
    use_sandbox: bool
    base_url: str

    @property
    def api_key_loaded(self) -> bool:
        return bool(self.api_key)

    def diagnostics(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "environment": self.environment,
            "use_sandbox": self.use_sandbox,
            "base_url": self.base_url,
            "username": self.username,
            "api_key_loaded": self.api_key_loaded,
            "api_key_masked": _mask_value(self.api_key),
            "sender_id_configured": bool(self.sender_id),
            "sender_id_masked": _mask_value(self.sender_id),
        }


@dataclass(frozen=True, slots=True)
class CelcomConfig:
    provider: str
    partner_id: str
    api_key: str
    shortcode: str
    base_url: str
    pass_type: str

    @property
    def api_key_loaded(self) -> bool:
        return bool(self.api_key)

    def diagnostics(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "base_url": self.base_url,
            "partner_id": self.partner_id,
            "api_key_loaded": self.api_key_loaded,
            "api_key_masked": _mask_value(self.api_key),
            "shortcode_configured": bool(self.shortcode),
            "shortcode_masked": _mask_value(self.shortcode),
            "pass_type": self.pass_type,
        }


def get_africas_talking_config(*, require_credentials: bool = True) -> AfricasTalkingConfig:
    environment = _normalize_environment(getattr(settings, "AFRICAS_TALKING_ENVIRONMENT", SANDBOX_ENVIRONMENT))
    use_sandbox = _resolve_use_sandbox(environment=environment)
    username = str(getattr(settings, "AFRICAS_TALKING_USERNAME", "")).strip()
    api_key = str(getattr(settings, "AFRICAS_TALKING_API_KEY", "")).strip()
    sender_id = str(getattr(settings, "AFRICAS_TALKING_SENDER_ID", "")).strip()
    configured_base_url = str(getattr(settings, "AFRICAS_TALKING_BASE_URL", "")).strip()
    base_url = configured_base_url or (
        AFRICAS_TALKING_SANDBOX_BASE_URL if use_sandbox else AFRICAS_TALKING_LIVE_BASE_URL
    )

    if require_credentials:
        missing = []
        if not username:
            missing.append("AFRICAS_TALKING_USERNAME")
        if not api_key:
            missing.append("AFRICAS_TALKING_API_KEY")
        if missing:
            raise SMSConfigurationError(
                f"Missing required Africa's Talking settings: {', '.join(missing)}."
            )

    if username:
        normalized_username = username.lower()
        if use_sandbox and normalized_username != AFRICAS_TALKING_SANDBOX_USERNAME:
            raise SMSConfigurationError("Sandbox mode requires AFRICAS_TALKING_USERNAME=sandbox.")
        if not use_sandbox and normalized_username == AFRICAS_TALKING_SANDBOX_USERNAME:
            raise SMSConfigurationError("Live mode cannot use AFRICAS_TALKING_USERNAME=sandbox.")

    return AfricasTalkingConfig(
        provider=SMS_PROVIDER_AFRICAS_TALKING,
        username=username,
        api_key=api_key,
        sender_id=sender_id,
        environment=environment,
        use_sandbox=use_sandbox,
        base_url=base_url,
    )


def get_celcom_config(*, require_credentials: bool = True) -> CelcomConfig:
    partner_id = str(getattr(settings, "CELCOM_PARTNER_ID", "")).strip()
    api_key = str(getattr(settings, "CELCOM_API_KEY", "")).strip()
    shortcode = str(getattr(settings, "CELCOM_SHORTCODE", "")).strip()
    base_url = str(getattr(settings, "CELCOM_BASE_URL", "")).strip() or CELCOM_SMS_BASE_URL
    pass_type = str(getattr(settings, "CELCOM_PASS_TYPE", "plain") or "plain").strip().lower() or "plain"

    if pass_type not in {"plain", "bm5"}:
        raise SMSConfigurationError("CELCOM_PASS_TYPE must be either 'plain' or 'bm5'.")

    if require_credentials:
        missing = []
        if not partner_id:
            missing.append("CELCOM_PARTNER_ID")
        if not api_key:
            missing.append("CELCOM_API_KEY")
        if not shortcode:
            missing.append("CELCOM_SHORTCODE")
        if missing:
            raise SMSConfigurationError(f"Missing required Celcom settings: {', '.join(missing)}.")

    return CelcomConfig(
        provider=SMS_PROVIDER_CELCOM,
        partner_id=partner_id,
        api_key=api_key,
        shortcode=shortcode,
        base_url=base_url,
        pass_type=pass_type,
    )
