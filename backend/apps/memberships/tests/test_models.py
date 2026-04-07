from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.memberships.models import Membership, TeamInvitation
from apps.teams.services import create_team_with_owner

User = get_user_model()


class MembershipModelTests(TestCase):
    def test_duplicate_membership_is_prevented(self) -> None:
        owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        member = User.objects.create_user(email="member@example.com", password="StrongPass123!", name="Member")
        team = create_team_with_owner(created_by=owner, name="Infra")

        Membership.objects.create(team=team, user=member, role=Membership.Role.MEMBER)

        with self.assertRaises(IntegrityError):
            Membership.objects.create(team=team, user=member, role=Membership.Role.MANAGER)

    def test_invitation_expiry_property(self) -> None:
        owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        team = create_team_with_owner(created_by=owner, name="Ops")
        invitation = TeamInvitation.objects.create(
            team=team,
            email="invitee@example.com",
            role=Membership.Role.MEMBER,
            invited_by=owner,
            expires_at=timezone.now() - timedelta(minutes=1),
        )

        self.assertTrue(invitation.is_expired)
