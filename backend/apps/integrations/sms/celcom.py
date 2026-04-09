from __future__ import annotations

import json
import logging
from urllib import error, request

from apps.integrations.sms.base import BaseSMSProvider
from apps.integrations.sms.config import get_celcom_config
from apps.integrations.sms.exceptions import SMSSendFailedError
from apps.integrations.validators import sanitize_provider_error

logger = logging.getLogger(__name__)


class CelcomSMSProvider(BaseSMSProvider):
    provider_name = "celcom"

    def __init__(self) -> None:
        config = get_celcom_config()
        self.partner_id = config.partner_id
        self.api_key = config.api_key
        self.shortcode = config.shortcode
        self.pass_type = config.pass_type
        self._api_url = config.base_url
        self._diagnostics = config.diagnostics()

    @property
    def api_url(self) -> str:
        return self._api_url

    def _normalize_mobile(self, value: str) -> str:
        digits = "".join(char for char in str(value or "") if char.isdigit())
        if digits.startswith("0"):
            return f"254{digits[1:]}"
        return digits

    def send_sms(self, to: str, message: str, metadata: dict | None = None) -> dict[str, object]:
        payload = {
            "partnerID": self.partner_id,
            "apikey": self.api_key,
            "mobile": self._normalize_mobile(to),
            "message": message,
            "shortcode": self.shortcode,
            "pass_type": self.pass_type,
        }

        req = request.Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            logger.info(
                "Sending Celcom SMS partner_id=%s api_key_loaded=%s api_key=%s shortcode=%s",
                self.partner_id,
                self._diagnostics["api_key_loaded"],
                self._diagnostics["api_key_masked"],
                self._diagnostics["shortcode_masked"],
            )
            with request.urlopen(req, timeout=20) as response:
                raw_body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            try:
                response_payload = json.loads(exc.read().decode("utf-8"))
            except Exception:
                response_payload = {}
            error_message = self._extract_error_message(response_payload) or "SMS delivery failed."
            raise SMSSendFailedError(
                sanitize_provider_error(Exception(str(error_message)), fallback_message="SMS delivery failed.")
            ) from exc
        except error.URLError as exc:
            raise SMSSendFailedError("SMS provider is currently unavailable.") from exc

        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise SMSSendFailedError("SMS provider returned an invalid response.") from exc

        responses = data.get("responses") or []
        if not responses:
            raise SMSSendFailedError("SMS provider did not confirm the recipient.")

        response_item = responses[0]
        response_code = str(response_item.get("respose-code", response_item.get("response-code", ""))).strip()
        response_description = str(response_item.get("response-description", "")).strip() or "SMS delivery failed."
        if response_code != "200":
            raise SMSSendFailedError(response_description)

        status_text = response_description.lower()
        resolved_status = "delivered" if "deliver" in status_text else "sent"

        return {
            "provider": self.provider_name,
            "message_id": str(response_item.get("messageid", "")),
            "status": resolved_status,
            "provider_status": response_description,
            "recipient": str(response_item.get("mobile", payload["mobile"])),
            "network_id": str(response_item.get("networkid", "")),
            "response": data,
        }

    def _extract_error_message(self, response_payload: dict) -> str:
        if not isinstance(response_payload, dict):
            return ""
        responses = response_payload.get("responses") or []
        if responses and isinstance(responses[0], dict):
            return str(responses[0].get("response-description", "")).strip()
        return str(response_payload.get("message") or response_payload.get("detail") or "").strip()
