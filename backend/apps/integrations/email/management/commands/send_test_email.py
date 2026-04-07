from __future__ import annotations

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a test email using the currently configured email backend."

    def add_arguments(self, parser):
        parser.add_argument("--to", required=True, help="Recipient email address.")
        parser.add_argument("--subject", default="WorkNest SMTP test", help="Email subject.")
        parser.add_argument(
            "--message",
            default="This is a test email from WorkNest. Your SMTP configuration is working.",
            help="Plain text email body.",
        )

    def handle(self, *args, **options):
        recipient = str(options["to"]).strip()
        if not recipient:
            raise CommandError("A recipient email is required.")

        delivered = send_mail(
            subject=str(options["subject"]),
            message=str(options["message"]),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )

        if delivered != 1:
            raise CommandError("The email backend did not confirm delivery.")

        self.stdout.write(self.style.SUCCESS(f"Sent test email to {recipient}"))
