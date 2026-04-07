from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied

from apps.memberships.models import Membership
from apps.teams.permissions import require_team_admin
from apps.teams.services import create_team_with_owner

User = get_user_model()


class TeamPermissionTests(TestCase):
    def test_require_team_admin_rejects_member(self) -> None:
        owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        member = User.objects.create_user(email="member@example.com", password="StrongPass123!", name="Member")
        team = create_team_with_owner(created_by=owner, name="Core")
        team.memberships.create(
            user=member,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=owner,
        )

        with self.assertRaises(PermissionDenied):
            require_team_admin(team=team, user=member)
