from __future__ import annotations

import json
from urllib import error, parse, request

import logging

from apps.integrations.sms.base import BaseSMSProvider
from apps.integrations.sms.config import get_africas_talking_config
from apps.integrations.sms.exceptions import SMSSendFailedError
from apps.integrations.validators import sanitize_provider_error

logger = logging.getLogger(__name__)


class AfricasTalkingSMSProvider(BaseSMSProvider):
    provider_name = "africas_talking"

    def __init__(self) -> None:
        config = get_africas_talking_config()
        self.username = config.username
        self.api_key = config.api_key
        self.sender_id = config.sender_id
        self.environment = config.environment
        self.use_sandbox = config.use_sandbox
        self._api_url = config.base_url
        self._diagnostics = config.diagnostics()

    @property
    def api_url(self) -> str:
        return self._api_url

    def send_sms(self, to: str, message: str, metadata: dict | None = None) -> dict[str, object]:
        payload = {
            "username": self.username,
            "to": to,
            "message": message,
        }
        if self.sender_id:
            payload["from"] = self.sender_id

        encoded_payload = parse.urlencode(payload).encode("utf-8")
        req = request.Request(
            self.api_url,
            data=encoded_payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "apiKey": self.api_key,
            },
            method="POST",
        )

        try:
            logger.info(
                "Sending Africa's Talking SMS environment=%s username=%s api_key_loaded=%s api_key=%s",
                self.environment,
                self.username,
                self._diagnostics["api_key_loaded"],
                self._diagnostics["api_key_masked"],
            )
            with request.urlopen(req, timeout=20) as response:
                raw_body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            try:
                response_payload = json.loads(exc.read().decode("utf-8"))
                error_message = (
                    response_payload.get("SMSMessageData", {}).get("Message")
                    or response_payload.get("errorMessage")
                    or "SMS delivery failed."
                )
            except Exception:
                error_message = "SMS delivery failed."
            raise SMSSendFailedError(
                sanitize_provider_error(Exception(str(error_message)), fallback_message="SMS delivery failed.")
            ) from exc
        except error.URLError as exc:
            raise SMSSendFailedError("SMS provider is currently unavailable.") from exc

        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise SMSSendFailedError("SMS provider returned an invalid response.") from exc

        recipients = data.get("SMSMessageData", {}).get("Recipients") or []
        recipient_data = recipients[0] if recipients else {}
        if not recipient_data:
            raise SMSSendFailedError("SMS provider did not confirm the recipient.")
        status_text = str(recipient_data.get("status") or data.get("SMSMessageData", {}).get("Message") or "").lower()
        if any(fragment in status_text for fragment in ("error", "invalid", "failed", "reject")):
            raise SMSSendFailedError("SMS provider rejected the message.")
        resolved_status = "delivered" if "deliver" in status_text else "sent"

        return {
            "provider": self.provider_name,
            "message_id": str(recipient_data.get("messageId", "")),
            "status": resolved_status,
            "provider_status": str(recipient_data.get("status", "")),
            "cost": str(recipient_data.get("cost", "")),
            "recipient": str(recipient_data.get("number", to)),
            "response": {
                "message": data.get("SMSMessageData", {}).get("Message", ""),
                "recipients": recipients,
            },
        }
