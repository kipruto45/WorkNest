from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings

from apps.integrations.constants import EMAIL_PROVIDER_SENDGRID
from apps.integrations.email.base import BaseEmailProvider, EmailMessagePayload
from apps.integrations.exceptions import EmailSendFailedError, IntegrationConfigurationError
from apps.integrations.validators import (
    sanitize_provider_error,
    validate_email_recipients,
    validate_email_subject,
)


class SendGridEmailProvider(BaseEmailProvider):
    provider_name = EMAIL_PROVIDER_SENDGRID
    api_url = "https://api.sendgrid.com/v3/mail/send"

    def __init__(self, *, api_key: str | None = None, timeout: int = 30) -> None:
        self.api_key = api_key or getattr(settings, "SENDGRID_API_KEY", "")
        self.timeout = timeout
        if not self.api_key:
            raise IntegrationConfigurationError("SendGrid email delivery requires SENDGRID_API_KEY.")

    def _post(self, payload: dict) -> None:
        request = Request(
            self.api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout):
                return None
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            message = sanitize_provider_error(
                Exception(body),
                fallback_message="Email delivery failed for the SendGrid provider.",
            )
            raise EmailSendFailedError(message) from exc
        except URLError as exc:
            raise EmailSendFailedError("SendGrid could not be reached.") from exc

    def send_email(self, payload: EmailMessagePayload) -> dict:
        recipients = validate_email_recipients(payload.to)
        subject = validate_email_subject(payload.subject)
        sendgrid_payload = {
            "personalizations": [
                {
                    "to": [{"email": email} for email in recipients],
                }
            ],
            "from": {"email": payload.from_email or settings.DEFAULT_FROM_EMAIL},
            "subject": subject,
            "content": [{"type": "text/plain", "value": payload.text_body}],
        }
        custom_args = payload.provider_metadata.get("custom_args") or {}
        if payload.metadata:
            custom_args = {
                **custom_args,
                **{key: str(value) for key, value in payload.metadata.items() if value is not None},
            }
        if custom_args:
            sendgrid_payload["custom_args"] = custom_args
        categories = payload.provider_metadata.get("categories") or []
        if categories:
            sendgrid_payload["categories"] = [str(item) for item in categories]
        if payload.html_body:
            sendgrid_payload["content"].append({"type": "text/html", "value": payload.html_body})
        if payload.reply_to:
            sendgrid_payload["reply_to_list"] = [{"email": email} for email in payload.reply_to]
        if payload.headers:
            sendgrid_payload["headers"] = payload.headers

        self._post(sendgrid_payload)
        return {
            "provider": self.provider_name,
            "recipient_count": len(recipients),
            "metadata": payload.metadata,
        }
