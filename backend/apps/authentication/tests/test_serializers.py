from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.authentication.serializers import RegisterSerializer
from apps.users.serializers import UserProfileUpdateSerializer

User = get_user_model()


class RegisterSerializerTests(TestCase):
    def test_register_serializer_rejects_duplicate_email(self) -> None:
        User.objects.create_user(email="jane@example.com", password="StrongPass123!", name="Jane")
        serializer = RegisterSerializer(
            data={
                "name": "Jane Again",
                "email": "jane@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_register_serializer_rejects_mismatched_passwords(self) -> None:
        serializer = RegisterSerializer(
            data={
                "name": "Jane Again",
                "email": "jane@example.com",
                "password": "StrongPass123!",
                "password_confirm": "Mismatch123!",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("password_confirm", serializer.errors)

    def test_register_serializer_rejects_weak_password(self) -> None:
        serializer = RegisterSerializer(
            data={
                "name": "Jane Again",
                "email": "jane@example.com",
                "password": "12345678",
                "password_confirm": "12345678",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)


class UserProfileUpdateSerializerTests(TestCase):
    def test_profile_update_rejects_invalid_timezone(self) -> None:
        serializer = UserProfileUpdateSerializer(
            data={"name": "Jane Doe", "timezone": "Mars/Phobos"},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("timezone", serializer.errors)
