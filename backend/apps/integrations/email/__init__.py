from apps.integrations.email.base import BaseEmailProvider, EmailMessagePayload, QueuedEmailPayload
from apps.integrations.email.services import get_email_provider, queue_email, send_system_email
from apps.integrations.email.smtp import SMTPEmailProvider
from apps.integrations.email.sendgrid import SendGridEmailProvider

__all__ = [
    "BaseEmailProvider",
    "EmailMessagePayload",
    "QueuedEmailPayload",
    "SMTPEmailProvider",
    "SendGridEmailProvider",
    "get_email_provider",
    "queue_email",
    "send_system_email",
]
