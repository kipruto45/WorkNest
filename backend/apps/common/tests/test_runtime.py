import importlib

from django.conf import settings
from django.test import SimpleTestCase


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
