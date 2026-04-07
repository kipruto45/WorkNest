from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string

from apps.users.models import User


DEFAULT_ADMIN_EMAIL = "admin@worknest.local"
DEFAULT_ADMIN_NAME = "WorkNest Admin"
DEFAULT_ADMIN_PASSWORD = "WorkNest123!"


class Command(BaseCommand):
    help = "Create or update a bootstrap admin user with known credentials."

    def add_arguments(self, parser):
        parser.add_argument("--email", default=DEFAULT_ADMIN_EMAIL, help="Admin email address.")
        parser.add_argument("--name", default=DEFAULT_ADMIN_NAME, help="Admin display name.")
        parser.add_argument(
            "--password",
            default=DEFAULT_ADMIN_PASSWORD,
            help=f"Admin password. Defaults to {DEFAULT_ADMIN_PASSWORD}.",
        )
        parser.add_argument(
            "--random-password",
            action="store_true",
            help="Generate a random password instead of using --password.",
        )

    def handle(self, *args, **options):
        email = str(options["email"]).strip().lower() or DEFAULT_ADMIN_EMAIL
        name = str(options["name"]).strip() or DEFAULT_ADMIN_NAME
        password = get_random_string(20) if options["random_password"] else str(options["password"]).strip() or DEFAULT_ADMIN_PASSWORD

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "name": name,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "email_verified": True,
            },
        )

        updated_fields: list[str] = []
        expected_values = {
            "name": name,
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
            "email_verified": True,
        }
        for field, value in expected_values.items():
            if getattr(user, field) != value:
                setattr(user, field, value)
                updated_fields.append(field)

        user.set_password(password)
        updated_fields.append("password")
        user.save(update_fields=list(dict.fromkeys(updated_fields + ["updated_at"])))

        state = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{state} admin user successfully."))
        self.stdout.write(f"email={email}")
        self.stdout.write(f"password={password}")
