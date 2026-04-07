from django.test import TestCase, override_settings

from apps.integrations.constants import EMAIL_PROVIDER_SENDGRID, STORAGE_PROVIDER_LOCAL
from apps.integrations.exceptions import IntegrationConfigurationError
from apps.integrations.services import validate_integrations_configuration


class IntegrationServiceTests(TestCase):
    @override_settings(
        EMAIL_PROVIDER="smtp",
        DEFAULT_FROM_EMAIL="no-reply@example.com",
        ATTACHMENTS_STORAGE_BACKEND=STORAGE_PROVIDER_LOCAL,
        MEDIA_URL="/media/",
        GOOGLE_OAUTH_CLIENT_ID="",
        GOOGLE_OAUTH_CLIENT_SECRET="",
    )
    def test_validate_integrations_configuration_returns_provider_summary(self) -> None:
        result = validate_integrations_configuration()

        self.assertEqual(result["email_provider"], "smtp")
        self.assertEqual(result["storage_provider"], "local")
        self.assertFalse(result["google_oauth_enabled"])

    @override_settings(
        EMAIL_PROVIDER=EMAIL_PROVIDER_SENDGRID,
        SENDGRID_API_KEY="",
        DEFAULT_FROM_EMAIL="no-reply@example.com",
        ATTACHMENTS_STORAGE_BACKEND="local",
        MEDIA_URL="/media/",
    )
    def test_validate_integrations_configuration_raises_for_missing_sendgrid_key(self) -> None:
        with self.assertRaises(IntegrationConfigurationError):
            validate_integrations_configuration()

    @override_settings(
        EMAIL_PROVIDER="smtp",
        DEFAULT_FROM_EMAIL="no-reply@example.com",
        ATTACHMENTS_STORAGE_BACKEND=STORAGE_PROVIDER_LOCAL,
        MEDIA_URL="/media/",
        GOOGLE_OAUTH_CLIENT_ID="client-id",
        GOOGLE_OAUTH_CLIENT_SECRET="",
    )
    def test_validate_integrations_configuration_raises_for_incomplete_google_config(self) -> None:
        with self.assertRaises(IntegrationConfigurationError):
            validate_integrations_configuration()
