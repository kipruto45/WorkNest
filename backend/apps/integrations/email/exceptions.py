from __future__ import annotations

from apps.integrations.exceptions import EmailDeliveryError


class EmailTemplateRenderError(EmailDeliveryError):
    """Raised when an email template cannot be rendered safely."""


class EmailJobConfigurationError(EmailDeliveryError):
    """Raised when an email job payload is incomplete or invalid."""
