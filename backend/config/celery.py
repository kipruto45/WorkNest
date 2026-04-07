"""Celery application entrypoint."""

from __future__ import annotations

import os

from celery import Celery


def _default_settings_module() -> str:
    if os.environ.get("ENVIRONMENT", "").strip().lower() == "production":
        return "config.settings.production"
    return "config.settings.local"


os.environ.setdefault("DJANGO_SETTINGS_MODULE", _default_settings_module())

app = Celery("config")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
