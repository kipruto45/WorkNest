from __future__ import annotations

import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.integrations.constants import SMS_PROVIDER_AFRICAS_TALKING
from apps.integrations.sms.config import get_africas_talking_config
from apps.integrations.sms.exceptions import SMSConfigurationError


class Command(BaseCommand):
    help = "Print the resolved Africa's Talking SMS configuration with secrets masked."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--format",
            choices=("text", "json"),
            default="text",
            help="Output format.",
        )

    def handle(self, *args, **options) -> None:
        output_format = options["format"]
        summary = {
            "enabled": bool(getattr(settings, "SMS_ENABLED", False)),
            "provider": str(getattr(settings, "SMS_PROVIDER", "")).strip() or SMS_PROVIDER_AFRICAS_TALKING,
            "settings_module": os.environ.get("DJANGO_SETTINGS_MODULE", ""),
            "app_environment": str(getattr(settings, "ENVIRONMENT", "")).strip(),
        }

        try:
            config = get_africas_talking_config()
        except SMSConfigurationError as exc:
            summary["valid"] = False
            summary["error"] = str(exc)
            self._write_summary(summary, output_format=output_format)
            raise CommandError(str(exc)) from exc

        summary["valid"] = True
        summary.update(config.diagnostics())
        self._write_summary(summary, output_format=output_format)

    def _write_summary(self, summary: dict[str, object], *, output_format: str) -> None:
        if output_format == "json":
            self.stdout.write(json.dumps(summary, indent=2, sort_keys=True))
            return

        for key, value in summary.items():
            self.stdout.write(f"{key}: {value}")
