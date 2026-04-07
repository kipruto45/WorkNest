from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit_logs.constants import AuditAction
from apps.audit_logs.models import AuditLog
from apps.memberships.models import Membership, TeamInvitation
from apps.notifications.constants import NotificationType
from apps.notifications.models import Notification
from apps.teams.services import create_team_with_owner

User = get_user_model()


class InvitationWorkflowTests(APITestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        self.manager = User.objects.create_user(email="manager@example.com", password="StrongPass123!", name="Manager")
        self.invited_user = User.objects.create_user(
            email="invitee@example.com",
            password="StrongPass123!",
            name="Invitee",
        )
        self.wrong_user = User.objects.create_user(email="wrong@example.com", password="StrongPass123!", name="Wrong User")
        self.team = create_team_with_owner(created_by=self.owner, name="Platform")
        self.team.memberships.create(
            team=self.team,
            user=self.manager,
            role=Membership.Role.MANAGER,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
        )

    def authenticate(self, user) -> None:
        access = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def create_invitation(self, **overrides) -> TeamInvitation:
        payload = {
            "team": self.team,
            "email": self.invited_user.email,
            "role": Membership.Role.MEMBER,
            "invited_by": self.owner,
            "expires_at": timezone.now() + timedelta(days=2),
        }
        payload.update(overrides)
        return TeamInvitation.objects.create(**payload)

    def test_public_invitation_detail_endpoint_returns_workspace_context(self) -> None:
        invitation = self.create_invitation(custom_message="Come help us ship.")

        response = self.client.get(reverse("api_v1:memberships:detail", args=[invitation.token]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["team"]["name"], self.team.name)
        self.assertEqual(response.data["data"]["email"], self.invited_user.email)
        self.assertEqual(response.data["data"]["custom_message"], "Come help us ship.")

    def test_invitation_creation_saves_custom_message_and_sends_email(self) -> None:
        self.authenticate(self.owner)

        response = self.client.post(
            reverse("api_v1:teams:invitations", args=[self.team.id]),
            {
                "email": "newmember@example.com",
                "role": Membership.Role.MANAGER,
                "custom_message": "Please start with the delivery board.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        invitation = TeamInvitation.objects.get(email="newmember@example.com")
        self.assertEqual(invitation.custom_message, "Please start with the delivery board.")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Please start with the delivery board.", mail.outbox[0].alternatives[0][0])

    def test_manager_can_invite_when_team_setting_allows_it(self) -> None:
        self.team.allow_manager_invites = True
        self.team.save(update_fields=["allow_manager_invites"])
        self.authenticate(self.manager)

        response = self.client.post(
            reverse("api_v1:teams:invitations", args=[self.team.id]),
            {"email": "managerinvite@example.com", "role": Membership.Role.MEMBER},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_duplicate_pending_invitation_is_blocked(self) -> None:
        self.authenticate(self.owner)
        self.create_invitation(email="duplicate@example.com")

        response = self.client.post(
            reverse("api_v1:teams:invitations", args=[self.team.id]),
            {"email": "duplicate@example.com", "role": Membership.Role.MEMBER},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_wrong_account_cannot_accept_invitation(self) -> None:
        invitation = self.create_invitation()
        self.authenticate(self.wrong_user)

        response = self.client.post(reverse("api_v1:memberships:accept", args=[invitation.token]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, TeamInvitation.Status.PENDING)

    def test_accept_invitation_creates_membership_notification_and_audit_log(self) -> None:
        invitation = self.create_invitation()
        self.authenticate(self.invited_user)

        response = self.client.post(reverse("api_v1:memberships:accept", args=[invitation.token]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, TeamInvitation.Status.ACCEPTED)
        self.assertIsNotNone(invitation.accepted_at)
        self.assertTrue(
            Membership.objects.filter(team=self.team, user=self.invited_user, status=Membership.Status.ACTIVE).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.owner,
                type=NotificationType.INVITATION_ACCEPTED,
                target_id=invitation.id,
            ).exists()
        )
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.INVITATION_ACCEPTED, target_id=str(invitation.id)).exists())

    def test_decline_invitation_records_notification_and_timestamp(self) -> None:
        invitation = self.create_invitation()
        self.authenticate(self.invited_user)

        response = self.client.post(reverse("api_v1:memberships:decline", args=[invitation.token]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, TeamInvitation.Status.DECLINED)
        self.assertIsNotNone(invitation.declined_at)
        self.assertTrue(
            Notification.objects.filter(
                user=self.owner,
                type=NotificationType.INVITATION_DECLINED,
                target_id=invitation.id,
            ).exists()
        )

    def test_resend_invitation_rotates_token_and_logs_action(self) -> None:
        invitation = self.create_invitation(email="resend@example.com")
        original_token = invitation.token
        original_expiry = invitation.expires_at
        self.authenticate(self.owner)

        response = self.client.post(reverse("api_v1:memberships:resend", args=[invitation.id]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertNotEqual(invitation.token, original_token)
        self.assertGreater(invitation.expires_at, original_expiry)
        self.assertEqual(invitation.status, TeamInvitation.Status.PENDING)
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.INVITATION_RESENT, target_id=str(invitation.id)).exists())

    def test_revoke_invitation_marks_it_revoked(self) -> None:
        invitation = self.create_invitation(email="revoke@example.com")
        self.authenticate(self.owner)

        response = self.client.post(reverse("api_v1:memberships:revoke", args=[invitation.id]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, TeamInvitation.Status.REVOKED)
        self.assertIsNotNone(invitation.revoked_at)
        self.assertTrue(AuditLog.objects.filter(action=AuditAction.INVITATION_REVOKED, target_id=str(invitation.id)).exists())

    def test_admin_can_update_invitation_role_before_acceptance(self) -> None:
        invitation = self.create_invitation(role=Membership.Role.MEMBER)
        self.authenticate(self.owner)

        response = self.client.patch(
            reverse("api_v1:teams:invitation-role", args=[self.team.id, invitation.id]),
            {"role": Membership.Role.MANAGER},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        invitation.refresh_from_db()
        self.assertEqual(invitation.role, Membership.Role.MANAGER)
        self.assertTrue(
            AuditLog.objects.filter(action=AuditAction.INVITATION_ROLE_UPDATED, target_id=str(invitation.id)).exists()
        )

    def test_archived_team_invitation_cannot_be_accepted(self) -> None:
        invitation = self.create_invitation()
        self.team.is_archived = True
        self.team.save(update_fields=["is_archived"])
        self.authenticate(self.invited_user)

        response = self.client.post(reverse("api_v1:memberships:accept", args=[invitation.token]), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
