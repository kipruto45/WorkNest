from django.contrib.auth import get_user_model
from django.test import TestCase


class UserModelTests(TestCase):
    def test_create_user_normalizes_email(self) -> None:
        user = get_user_model().objects.create_user(
            email="Person@Example.COM",
            password="strong-password-123",
            name="Person Example",
        )

        self.assertEqual(user.email, "Person@example.com")
        self.assertTrue(user.check_password("strong-password-123"))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertEqual(user.auth_provider, "email")
        self.assertFalse(user.email_verified)

    def test_create_superuser_sets_required_flags(self) -> None:
        admin_user = get_user_model().objects.create_superuser(
            email="admin@example.com",
            password="strong-password-123",
            name="Admin Example",
        )

        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)

    def test_user_str_returns_email(self) -> None:
        user = get_user_model().objects.create_user(
            email="member@example.com",
            password="strong-password-123",
            name="Member Example",
        )

        self.assertEqual(str(user), "member@example.com")

    def test_create_user_requires_name(self) -> None:
        with self.assertRaisesMessage(ValueError, "The name field must be set."):
            get_user_model().objects.create_user(
                email="member@example.com",
                password="strong-password-123",
                name="",
            )
