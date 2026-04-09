from __future__ import annotations

from apps.integrations.exceptions import IntegrationConfigurationError, IntegrationError


class SMSIntegrationError(IntegrationError):
    """Base SMS integration exception."""


class SMSConfigurationError(IntegrationConfigurationError, SMSIntegrationError):
    """Raised when SMS provider settings are missing or invalid."""


class SMSSendFailedError(SMSIntegrationError):
    """Raised when an SMS provider rejects or fails a send request."""
