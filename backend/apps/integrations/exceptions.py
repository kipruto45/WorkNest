from __future__ import annotations


class IntegrationError(Exception):
    """Base integration-layer exception."""


class IntegrationValidationError(IntegrationError):
    """Raised when integration input validation fails."""


class IntegrationConfigurationError(IntegrationError):
    """Raised when required provider configuration is missing or invalid."""


class ExternalProviderUnavailableError(IntegrationError):
    """Raised when an external provider cannot be reached."""


class EmailDeliveryError(IntegrationError):
    """Raised when email delivery fails."""


class EmailSendFailedError(EmailDeliveryError):
    """Raised when an email provider rejects or fails a send request."""


class StorageProviderError(IntegrationError):
    """Raised when a storage provider operation fails."""


class StorageUploadFailedError(StorageProviderError):
    """Raised when a storage upload fails."""


class StorageDeleteFailedError(StorageProviderError):
    """Raised when a storage delete fails."""


class StorageDownloadUrlError(StorageProviderError):
    """Raised when generating a storage download URL fails."""


class OAuthProviderError(IntegrationError):
    """Raised when an OAuth provider operation fails."""


class OAuthValidationFailedError(OAuthProviderError):
    """Raised when OAuth configuration or payload validation fails."""
