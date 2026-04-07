from django.test import TestCase

from apps.memberships.serializers import InviteMemberSerializer, UpdateMemberRoleSerializer


class MembershipSerializerTests(TestCase):
    def test_invite_serializer_normalizes_email(self) -> None:
        serializer = InviteMemberSerializer(data={"email": " MEMBER@Example.com ", "role": "member"})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["email"], "member@example.com")

    def test_invite_serializer_trims_custom_message(self) -> None:
        serializer = InviteMemberSerializer(
            data={"email": "member@example.com", "role": "member", "custom_message": "  Welcome aboard  "}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["custom_message"], "Welcome aboard")

    def test_role_update_serializer_rejects_invalid_role(self) -> None:
        serializer = UpdateMemberRoleSerializer(data={"role": "owner"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("role", serializer.errors)
