from django.test import RequestFactory, TestCase, override_settings

from apps.integrations.exceptions import OAuthValidationFailedError
from apps.integrations.oauth.services import get_google_oauth_config, handle_google_auth_request, verify_google_identity


class GoogleOAuthIntegrationTests(TestCase):
    def setUp(self) -> None:
        self.factory = RequestFactory()
        self.request = self.factory.get("/api/v1/auth/oauth/google/")
        self.request.build_absolute_uri = lambda path="/": f"http://testserver{path}"

    def test_google_oauth_config_reports_disabled_when_not_configured(self) -> None:
        payload = get_google_oauth_config(request=self.request)

        self.assertEqual(payload["provider"], "google")
        self.assertFalse(payload["enabled"])

    @override_settings(GOOGLE_OAUTH_CLIENT_ID="client", GOOGLE_OAUTH_CLIENT_SECRET="secret")
    def test_google_auth_request_returns_login_url_when_configured(self) -> None:
        payload = handle_google_auth_request(request=self.request)

        self.assertEqual(payload["provider"], "google")
        self.assertIn("https://accounts.google.com/o/oauth2/v2/auth", payload["login_url"])
        self.assertIn("client_id=client", payload["login_url"])

    @override_settings(
        GOOGLE_OAUTH_CLIENT_ID="client",
        GOOGLE_OAUTH_CLIENT_SECRET="secret",
        BACKEND_URL="https://api.worknest.test",
        GOOGLE_REDIRECT_URI="https://api.worknest.test/api/v1/auth/google/callback/",
    )
    def test_google_oauth_config_prefers_explicit_backend_urls(self) -> None:
        payload = get_google_oauth_config(request=self.request)

        self.assertIn("https://accounts.google.com/o/oauth2/v2/auth", payload["login_url"])
        self.assertIn("client_id=client", payload["login_url"])
        self.assertEqual(payload["callback_url"], "https://api.worknest.test/api/v1/auth/google/callback/")

    def test_verify_google_identity_rejects_missing_required_fields(self) -> None:
        with self.assertRaises(OAuthValidationFailedError):
            verify_google_identity(payload={"email": "user@example.com"})
