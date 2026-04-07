from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied

from apps.memberships.models import Membership
from apps.memberships.permissions import require_admin_membership
from apps.teams.services import create_team_with_owner

User = get_user_model()


class MembershipPermissionTests(TestCase):
    def test_require_admin_membership_rejects_non_admin(self) -> None:
        owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        member = User.objects.create_user(email="member@example.com", password="StrongPass123!", name="Member")
        team = create_team_with_owner(created_by=owner, name="Security")
        membership = Membership.objects.create(
            team=team,
            user=member,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=owner,
        )

        with self.assertRaises(PermissionDenied):
            require_admin_membership(membership=membership)
