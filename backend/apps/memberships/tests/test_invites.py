from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.memberships.models import Membership, TeamInvitation
from apps.teams.services import create_team_with_owner

User = get_user_model()


class TeamInvitationFlowTests(APITestCase):
    def authenticate(self, user) -> None:
        access = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_accept_invitation_activates_membership(self) -> None:
        owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        invited_user = User.objects.create_user(email="invitee@example.com", password="StrongPass123!", name="Invitee")
        team = create_team_with_owner(created_by=owner, name="Platform")
        invitation = TeamInvitation.objects.create(
            team=team,
            email=invited_user.email,
            role=Membership.Role.MEMBER,
            invited_by=owner,
            expires_at=timezone.now() + timedelta(days=1),
        )
        self.authenticate(invited_user)

        response = self.client.post(reverse("api_v1:memberships:accept", args=[invitation.token]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(team.memberships.filter(user=invited_user, status=Membership.Status.ACTIVE).exists())

    def test_decline_invitation_marks_it_declined(self) -> None:
        owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        invited_user = User.objects.create_user(email="invitee@example.com", password="StrongPass123!", name="Invitee")
        team = create_team_with_owner(created_by=owner, name="Platform")
        invitation = TeamInvitation.objects.create(
            team=team,
            email=invited_user.email,
            role=Membership.Role.MEMBER,
            invited_by=owner,
            expires_at=timezone.now() + timedelta(days=1),
        )
        self.authenticate(invited_user)

        response = self.client.post(reverse("api_v1:memberships:decline", args=[invitation.token]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, TeamInvitation.Status.DECLINED)

    def test_expired_invitation_is_rejected(self) -> None:
        owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        invited_user = User.objects.create_user(email="invitee@example.com", password="StrongPass123!", name="Invitee")
        team = create_team_with_owner(created_by=owner, name="Platform")
        invitation = TeamInvitation.objects.create(
            team=team,
            email=invited_user.email,
            role=Membership.Role.MEMBER,
            invited_by=owner,
            expires_at=timezone.now() - timedelta(minutes=5),
        )
        self.authenticate(invited_user)

        response = self.client.post(reverse("api_v1:memberships:accept", args=[invitation.token]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, TeamInvitation.Status.EXPIRED)
