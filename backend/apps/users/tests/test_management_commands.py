from io import StringIO

from django.core.management import call_command
from django.test import TestCase


class EnsureAdminUserCommandTests(TestCase):
    def test_command_does_not_echo_raw_password(self) -> None:
        stdout = StringIO()

        call_command(
            "ensure_admin_user",
            email="admin@worknest.local",
            name="WorkNest Admin",
            password="WorkNest123!",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("admin user successfully.", output)
        self.assertIn("email=admin@worknest.local", output)
        self.assertIn("password=[securely applied from input]", output)
        self.assertNotIn("WorkNest123!", output)
