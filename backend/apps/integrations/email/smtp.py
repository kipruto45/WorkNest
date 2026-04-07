from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from apps.integrations.constants import EMAIL_PROVIDER_SMTP
from apps.integrations.email.base import BaseEmailProvider, EmailMessagePayload
from apps.integrations.exceptions import EmailSendFailedError
from apps.integrations.validators import sanitize_provider_error, validate_email_recipients, validate_email_subject


class SMTPEmailProvider(BaseEmailProvider):
    provider_name = EMAIL_PROVIDER_SMTP

    def send_email(self, payload: EmailMessagePayload) -> dict:
        recipients = validate_email_recipients(payload.to)
        subject = validate_email_subject(payload.subject)

        message = EmailMultiAlternatives(
            subject=subject,
            body=payload.text_body,
            from_email=payload.from_email or settings.DEFAULT_FROM_EMAIL,
            to=recipients,
            reply_to=payload.reply_to,
            headers=payload.headers,
        )
        if payload.html_body:
            message.attach_alternative(payload.html_body, "text/html")

        try:
            message.send(fail_silently=False)
        except Exception as exc:  # pragma: no cover
            raise EmailSendFailedError(
                sanitize_provider_error(exc, fallback_message="Email delivery failed for the SMTP provider.")
            ) from exc

        return {
            "provider": self.provider_name,
            "recipient_count": len(recipients),
            "metadata": payload.metadata,
        }
