import importlib

from django.conf import settings
from django.test import SimpleTestCase

from config.settings import base as base_settings


class RuntimeConfigurationTests(SimpleTestCase):
    def test_production_settings_import_without_crashing(self) -> None:
        production = importlib.import_module("config.settings.production")

        self.assertFalse(production.DEBUG)
        self.assertTrue(production.SECURE_SSL_REDIRECT)
        self.assertEqual(production.AUTH_COOKIE_SAMESITE, "None")

    def test_celery_app_loads(self) -> None:
        from config.celery import app

        self.assertEqual(app.main, "config")
        self.assertEqual(app.conf.task_serializer, "json")

    def test_asgi_application_loads(self) -> None:
        from config.asgi import application

        self.assertTrue(callable(application))

    def test_environment_backed_settings_are_available(self) -> None:
        self.assertEqual(settings.API_VERSION, "v1")
        self.assertTrue(settings.REDIS_URL)
        self.assertIn("default", settings.DATABASES)

    def test_rediss_url_includes_ssl_cert_reqs_when_missing(self) -> None:
        normalized = base_settings._normalize_redis_connection_url(
            "rediss://example-redis:6379/0",
            ssl_cert_reqs="CERT_OPTIONAL",
        )

        self.assertEqual(normalized, "rediss://example-redis:6379/0?ssl_cert_reqs=CERT_OPTIONAL")

    def test_rediss_url_preserves_existing_ssl_cert_reqs(self) -> None:
        raw_url = "rediss://example-redis:6379/0?ssl_cert_reqs=CERT_NONE"

        normalized = base_settings._normalize_redis_connection_url(
            raw_url,
            ssl_cert_reqs="CERT_REQUIRED",
        )

        self.assertEqual(normalized, raw_url)

    def test_invalid_ssl_cert_reqs_defaults_to_cert_required(self) -> None:
        self.assertEqual(base_settings._normalize_redis_ssl_cert_reqs("invalid"), "CERT_REQUIRED")
