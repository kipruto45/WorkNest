from django.test import TestCase

from apps.memberships.models import Membership
from apps.users.models import User
from apps.users.serializers import CurrentUserSerializer, UserProfileUpdateSerializer


class UserSerializerTests(TestCase):
    def test_profile_update_rejects_short_name(self) -> None:
        serializer = UserProfileUpdateSerializer(data={"name": "J"}, partial=True)

        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_profile_update_rejects_long_bio(self) -> None:
        serializer = UserProfileUpdateSerializer(data={"bio": "x" * 1001}, partial=True)

        self.assertFalse(serializer.is_valid())
        self.assertIn("bio", serializer.errors)

    def test_current_user_serializer_recovers_missing_personal_workspace(self) -> None:
        user = User.objects.create_user(
            email="serializer-personal@example.com",
            password="StrongPass123!",
            name="Serializer Personal",
            account_type=User.AccountType.PERSONAL,
        )

        payload = CurrentUserSerializer(user).data

        self.assertTrue(payload.get("default_team_id"))
        self.assertTrue(
            Membership.objects.filter(
                user=user,
                status=Membership.Status.ACTIVE,
                team__is_personal=True,
                team__is_archived=False,
            ).exists()
        )
