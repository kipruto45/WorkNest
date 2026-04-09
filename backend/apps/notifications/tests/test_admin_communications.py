from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.memberships.models import Membership
from apps.notifications.constants import NotificationType
from apps.notifications.models import AdminCommunication, Notification
from apps.teams.services import create_team_with_owner

User = get_user_model()


class AdminCommunicationTests(APITestCase):
    def setUp(self) -> None:
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="StrongPass123!",
            name="Admin",
            is_staff=True,
        )
        self.user = User.objects.create_user(email="user@example.com", password="StrongPass123!", name="User")
        self.owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        self.member = User.objects.create_user(email="member@example.com", password="StrongPass123!", name="Member")
        self.team = create_team_with_owner(created_by=self.owner, name="Growth")
        self.team.memberships.create(
            user=self.member,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
        )

    def authenticate(self, user) -> None:
        access = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_admin_can_send_in_app_communication_to_all_users(self) -> None:
        self.authenticate(self.admin)

        response = self.client.post(
            reverse("api_v1:notifications:admin-communications"),
            {
                "audience_type": "all_users",
                "channel_type": "in_app",
                "title": "Platform update",
                "message": "We are rolling out new workspace controls tonight.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(AdminCommunication.objects.filter(title="Platform update").exists())
        self.assertTrue(
            Notification.objects.filter(user=self.user, type=NotificationType.ADMIN_MESSAGE).exists()
        )

    def test_admin_can_send_email_communication_to_selected_team(self) -> None:
        self.authenticate(self.admin)

        response = self.client.post(
            reverse("api_v1:notifications:admin-communications"),
            {
                "audience_type": "single_team",
                "channel_type": "email",
                "title": "Workspace upgrade",
                "message": "Your team workspace has new productivity templates.",
                "team_ids": [str(self.team.id)],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertGreaterEqual(len(mail.outbox), 1)

    def test_non_admin_is_rejected(self) -> None:
        self.authenticate(self.user)

        response = self.client.post(
            reverse("api_v1:notifications:admin-communications"),
            {
                "audience_type": "all_users",
                "channel_type": "in_app",
                "title": "Unauthorized",
                "message": "This should not send.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(SMS_ENABLED=True, CELERY_TASK_ALWAYS_EAGER=True, SMS_BROADCAST_CONFIRMATION_REQUIRED=True)
    def test_sms_broadcast_requires_confirmation_for_multi_recipient_send(self) -> None:
        self.member.phone_number = "+254711000001"
        self.member.sms_opt_in = True
        self.member.save(update_fields=["phone_number", "sms_opt_in", "updated_at"])
        self.owner.phone_number = "+254711000002"
        self.owner.sms_opt_in = True
        self.owner.save(update_fields=["phone_number", "sms_opt_in", "updated_at"])
        self.authenticate(self.admin)

        response = self.client.post(
            reverse("api_v1:notifications:admin-communications"),
            {
                "audience_type": "single_team",
                "channel_type": "sms",
                "title": "Urgent update",
                "message": "This should require confirmation.",
                "team_ids": [str(self.team.id)],
                "confirm_broadcast": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_broadcast", response.data["errors"])
