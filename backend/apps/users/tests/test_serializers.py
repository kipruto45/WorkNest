from django.test import TestCase

from apps.users.serializers import UserProfileUpdateSerializer


class UserSerializerTests(TestCase):
    def test_profile_update_rejects_short_name(self) -> None:
        serializer = UserProfileUpdateSerializer(data={"name": "J"}, partial=True)

        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_profile_update_rejects_long_bio(self) -> None:
        serializer = UserProfileUpdateSerializer(data={"bio": "x" * 1001}, partial=True)

        self.assertFalse(serializer.is_valid())
        self.assertIn("bio", serializer.errors)
