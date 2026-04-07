from __future__ import annotations

from django.core.checks import run_checks
from django.test import SimpleTestCase, override_settings


class IntegrationChecksTests(SimpleTestCase):
    @override_settings(
        EMAIL_PROVIDER="smtp",
        DEFAULT_FROM_EMAIL="no-reply@example.com",
        ATTACHMENTS_STORAGE_BACKEND="local",
        MEDIA_URL="/media/",
        GOOGLE_OAUTH_CLIENT_ID="",
        GOOGLE_OAUTH_CLIENT_SECRET="",
    )
    def test_system_checks_pass_for_valid_local_configuration(self) -> None:
        integration_errors = [error for error in run_checks() if error.id == "integrations.E001"]

        self.assertEqual(integration_errors, [])

    @override_settings(
        EMAIL_PROVIDER="sendgrid",
        SENDGRID_API_KEY="",
        DEFAULT_FROM_EMAIL="no-reply@example.com",
        ATTACHMENTS_STORAGE_BACKEND="local",
        MEDIA_URL="/media/",
    )
    def test_system_checks_report_invalid_sendgrid_configuration(self) -> None:
        integration_errors = [error for error in run_checks() if error.id == "integrations.E001"]

        self.assertEqual(len(integration_errors), 1)
        self.assertIn("SENDGRID_API_KEY", integration_errors[0].msg)

    @override_settings(
        EMAIL_PROVIDER="smtp",
        DEFAULT_FROM_EMAIL="no-reply@example.com",
        ATTACHMENTS_STORAGE_BACKEND="local",
        MEDIA_URL="/media/",
        GOOGLE_OAUTH_CLIENT_ID="client-id",
        GOOGLE_OAUTH_CLIENT_SECRET="",
    )
    def test_system_checks_report_incomplete_google_oauth_configuration(self) -> None:
        integration_errors = [error for error in run_checks() if error.id == "integrations.E001"]

        self.assertEqual(len(integration_errors), 1)
        self.assertIn("Google OAuth configuration is incomplete", integration_errors[0].msg)
