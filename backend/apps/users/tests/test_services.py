from django.test import TestCase, override_settings

from apps.users.models import User
from apps.users.services import bootstrap_admin_user


class UserServiceTests(TestCase):
    def test_bootstrap_admin_user_creates_admin_account(self) -> None:
        user, created = bootstrap_admin_user(
            email="admin@worknest.local",
            name="WorkNest Admin",
            password="WorkNest123!",
        )

        self.assertTrue(created)
        self.assertEqual(user.email, "admin@worknest.local")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)
        self.assertTrue(user.check_password("WorkNest123!"))

    def test_bootstrap_admin_user_repairs_existing_account(self) -> None:
        existing_user = User.objects.create_user(
            email="admin@worknest.local",
            password="old-password",
            name="Old Admin",
            is_staff=False,
            is_superuser=False,
            is_active=False,
            email_verified=False,
        )

        user, created = bootstrap_admin_user(
            email="admin@worknest.local",
            name="WorkNest Admin",
            password="WorkNest123!",
        )

        self.assertFalse(created)
        self.assertEqual(str(user.id), str(existing_user.id))
        self.assertEqual(user.name, "WorkNest Admin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertTrue(user.email_verified)
        self.assertTrue(user.check_password("WorkNest123!"))
