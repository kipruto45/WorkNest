from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

from apps.integrations.constants import DEFAULT_SUPABASE_TIMEOUT
from apps.integrations.exceptions import ExternalProviderUnavailableError, IntegrationConfigurationError
from apps.integrations.validators import sanitize_provider_error


class SupabaseClient:
    def __init__(self, *, base_url: str | None = None, api_key: str | None = None, timeout: int | None = None) -> None:
        self.base_url = (base_url if base_url is not None else getattr(settings, "SUPABASE_URL", "")).rstrip("/")
        self.api_key = (
            api_key
            if api_key is not None
            else getattr(settings, "SUPABASE_KEY", "") or getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "")
        )
        self.timeout = timeout or getattr(settings, "SUPABASE_TIMEOUT", DEFAULT_SUPABASE_TIMEOUT)
        missing = []
        if not self.base_url:
            missing.append("SUPABASE_URL")
        if not self.api_key:
            missing.append("SUPABASE_KEY")
        if missing:
            raise IntegrationConfigurationError(
                f"Supabase client requires {', '.join(sorted(missing))}."
            )

    def request(self, *, method: str, url: str, data: bytes | None = None, headers: dict[str, str] | None = None):
        request_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "apikey": self.api_key,
        }
        if headers:
            request_headers.update(headers)

        request = Request(url, data=data, headers=request_headers, method=method)
        try:
            return urlopen(request, timeout=self.timeout)
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            message = sanitize_provider_error(
                Exception(body),
                fallback_message="Supabase request failed.",
            )
            raise ExternalProviderUnavailableError(message) from exc
        except URLError as exc:
            raise ExternalProviderUnavailableError("Supabase could not be reached.") from exc
