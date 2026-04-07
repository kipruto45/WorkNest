from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.memberships.models import Membership
from apps.teams.services import create_team_with_owner

User = get_user_model()


class MembershipViewTests(APITestCase):
    def authenticate(self, user) -> None:
        access = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_admin_can_invite_member(self) -> None:
        owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        team = create_team_with_owner(created_by=owner, name="Backend")
        self.authenticate(owner)

        response = self.client.post(
            reverse("api_v1:teams:invite-member", args=[team.id]),
            {"email": "newmember@example.com", "role": Membership.Role.MEMBER},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["email"], "newmember@example.com")

    def test_non_admin_cannot_invite_member(self) -> None:
        owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        member = User.objects.create_user(email="member@example.com", password="StrongPass123!", name="Member")
        team = create_team_with_owner(created_by=owner, name="Backend")
        team.memberships.create(
            user=member,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=owner,
        )
        self.authenticate(member)

        response = self.client.post(
            reverse("api_v1:teams:invite-member", args=[team.id]),
            {"email": "newmember@example.com", "role": Membership.Role.MEMBER},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_member_role(self) -> None:
        owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        member = User.objects.create_user(email="member@example.com", password="StrongPass123!", name="Member")
        team = create_team_with_owner(created_by=owner, name="Backend")
        membership = team.memberships.create(
            user=member,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=owner,
        )
        self.authenticate(owner)

        response = self.client.patch(
            reverse("api_v1:teams:member-role", args=[team.id, membership.id]),
            {"role": Membership.Role.MANAGER},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["role"], Membership.Role.MANAGER)

    def test_admin_can_remove_member(self) -> None:
        owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        member = User.objects.create_user(email="member@example.com", password="StrongPass123!", name="Member")
        team = create_team_with_owner(created_by=owner, name="Backend")
        membership = team.memberships.create(
            user=member,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=owner,
        )
        self.authenticate(owner)

        response = self.client.delete(reverse("api_v1:teams:member-remove", args=[team.id, membership.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        membership.refresh_from_db()
        self.assertEqual(membership.status, Membership.Status.REMOVED)

    def test_last_admin_cannot_be_removed(self) -> None:
        owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        team = create_team_with_owner(created_by=owner, name="Backend")
        owner_membership = team.memberships.get(user=owner)
        self.authenticate(owner)

        response = self.client.delete(reverse("api_v1:teams:member-remove", args=[team.id, owner_membership.id]))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
