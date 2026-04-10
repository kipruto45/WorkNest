from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.memberships.models import Membership
from apps.teams.services import create_team_with_owner

User = get_user_model()


class TeamInviteLinkTests(APITestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        self.manager = User.objects.create_user(email="manager@example.com", password="StrongPass123!", name="Manager")
        self.member = User.objects.create_user(email="member@example.com", password="StrongPass123!", name="Member")
        self.invited_user = User.objects.create_user(email="invitee@example.com", password="StrongPass123!", name="Invitee")
        self.invited_user_2 = User.objects.create_user(email="invitee-two@example.com", password="StrongPass123!", name="Invitee Two")
        self.team = create_team_with_owner(created_by=self.owner, name="Delivery")
        Membership.objects.create(
            team=self.team,
            user=self.manager,
            role=Membership.Role.MANAGER,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
            joined_at=timezone.now(),
        )
        Membership.objects.create(
            team=self.team,
            user=self.member,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
            joined_at=timezone.now(),
        )

    def authenticate(self, user) -> None:
        token = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_admin_can_create_invite_links_with_unique_tokens(self) -> None:
        self.authenticate(self.owner)

        first_response = self.client.post(
            reverse("api_v1:invite_links:list-create", args=[self.team.id]),
            {"role": Membership.Role.MANAGER, "label": "Ops lead"},
            format="json",
        )
        second_response = self.client.post(
            reverse("api_v1:invite_links:list-create", args=[self.team.id]),
            {"role": Membership.Role.MEMBER, "label": "General member"},
            format="json",
        )

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(first_response.data["data"]["token"], second_response.data["data"]["token"])

    def test_member_cannot_list_or_create_invite_links(self) -> None:
        self.authenticate(self.member)

        list_response = self.client.get(reverse("api_v1:invite_links:list-create", args=[self.team.id]))
        create_response = self.client.post(
            reverse("api_v1:invite_links:list-create", args=[self.team.id]),
            {"role": Membership.Role.MEMBER},
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_only_generate_member_invite_links(self) -> None:
        self.team.allow_manager_invites = True
        self.team.save(update_fields=["allow_manager_invites", "updated_at"])
        self.authenticate(self.manager)

        member_link_response = self.client.post(
            reverse("api_v1:invite_links:list-create", args=[self.team.id]),
            {"role": Membership.Role.MEMBER, "label": "Coordinator share link"},
            format="json",
        )
        manager_link_response = self.client.post(
            reverse("api_v1:invite_links:list-create", args=[self.team.id]),
            {"role": Membership.Role.MANAGER},
            format="json",
        )

        self.assertEqual(member_link_response.status_code, status.HTTP_200_OK)
        self.assertEqual(manager_link_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_accept_invite_link_assigns_role_and_enforces_max_uses(self) -> None:
        self.authenticate(self.owner)
        create_response = self.client.post(
            reverse("api_v1:invite_links:list-create", args=[self.team.id]),
            {
                "role": Membership.Role.MANAGER,
                "max_uses": 1,
                "expires_at": (timezone.now() + timedelta(days=1)).isoformat(),
            },
            format="json",
        )
        token = create_response.data["data"]["token"]
        self.client.credentials()

        self.authenticate(self.invited_user)
        accept_response = self.client.post(reverse("api_v1:invite_links:accept", args=[token]), {}, format="json")

        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)
        membership = Membership.objects.get(team=self.team, user=self.invited_user)
        self.assertEqual(membership.role, Membership.Role.MANAGER)

        self.authenticate(self.invited_user_2)
        second_accept_response = self.client.post(reverse("api_v1:invite_links:accept", args=[token]), {}, format="json")
        self.assertEqual(second_accept_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(second_accept_response.data["errors"]["invite_link"], ["This invite link has reached its maximum uses."])

    def test_revoked_invite_link_cannot_be_accepted(self) -> None:
        self.authenticate(self.owner)
        create_response = self.client.post(
            reverse("api_v1:invite_links:list-create", args=[self.team.id]),
            {"role": Membership.Role.MEMBER},
            format="json",
        )
        invite_link_id = create_response.data["data"]["id"]
        token = create_response.data["data"]["token"]
        revoke_response = self.client.post(
            reverse("api_v1:invite_links:revoke", args=[self.team.id, invite_link_id]),
            {},
            format="json",
        )
        self.assertEqual(revoke_response.status_code, status.HTTP_200_OK)

        self.client.credentials()
        self.authenticate(self.invited_user)
        accept_response = self.client.post(reverse("api_v1:invite_links:accept", args=[token]), {}, format="json")
        self.assertEqual(accept_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(accept_response.data["errors"]["invite_link"], ["This invite link has been revoked."])

    def test_member_cannot_revoke_regenerate_or_copy_invite_links(self) -> None:
        self.authenticate(self.owner)
        create_response = self.client.post(
            reverse("api_v1:invite_links:list-create", args=[self.team.id]),
            {"role": Membership.Role.MEMBER},
            format="json",
        )
        invite_link_id = create_response.data["data"]["id"]

        self.authenticate(self.member)
        revoke_response = self.client.post(
            reverse("api_v1:invite_links:revoke", args=[self.team.id, invite_link_id]),
            {},
            format="json",
        )
        regenerate_response = self.client.post(
            reverse("api_v1:invite_links:regenerate", args=[self.team.id, invite_link_id]),
            {},
            format="json",
        )
        copy_response = self.client.post(
            reverse("api_v1:invite_links:copy", args=[self.team.id, invite_link_id]),
            {},
            format="json",
        )

        self.assertEqual(revoke_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(regenerate_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(copy_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_email_invites_are_role_limited(self) -> None:
        self.team.allow_manager_invites = True
        self.team.save(update_fields=["allow_manager_invites", "updated_at"])
        self.authenticate(self.manager)

        admin_invite_response = self.client.post(
            reverse("api_v1:teams:invitations", args=[self.team.id]),
            {"email": "admin-invite@example.com", "role": Membership.Role.ADMIN},
            format="json",
        )
        manager_invite_response = self.client.post(
            reverse("api_v1:teams:invitations", args=[self.team.id]),
            {"email": "manager-invite@example.com", "role": Membership.Role.MANAGER},
            format="json",
        )
        member_invite_response = self.client.post(
            reverse("api_v1:teams:invitations", args=[self.team.id]),
            {"email": "member-invite@example.com", "role": Membership.Role.MEMBER},
            format="json",
        )

        self.assertEqual(admin_invite_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(manager_invite_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(member_invite_response.status_code, status.HTTP_201_CREATED)
