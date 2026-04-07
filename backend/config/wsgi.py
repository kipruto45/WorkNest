"""WSGI config kept for compatibility with management tooling."""

import os

from django.core.wsgi import get_wsgi_application


def _default_settings_module() -> str:
    if os.environ.get("ENVIRONMENT", "").strip().lower() == "production":
        return "config.settings.production"
    return "config.settings.local"


os.environ.setdefault("DJANGO_SETTINGS_MODULE", _default_settings_module())

application = get_wsgi_application()
