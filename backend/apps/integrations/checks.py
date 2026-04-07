from __future__ import annotations

from django.core.checks import Error, Tags, register

from apps.integrations.exceptions import IntegrationConfigurationError
from apps.integrations.services import validate_integrations_configuration


@register(Tags.compatibility)
def integrations_configuration_check(app_configs=None, **kwargs):
    try:
        validate_integrations_configuration()
    except IntegrationConfigurationError as exc:
        return [
            Error(
                str(exc),
                id="integrations.E001",
            )
        ]
    return []
