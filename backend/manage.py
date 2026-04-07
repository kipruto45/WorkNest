#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys


def _default_settings_module() -> str:
    if os.environ.get("ENVIRONMENT", "").strip().lower() == "production":
        return "config.settings.production"
    return "config.settings.local"


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", _default_settings_module())
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and available on "
            "your PYTHONPATH environment variable? Did you forget to activate a "
            "virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
