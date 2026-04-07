from django.contrib.auth import get_user_model
from django.test import TestCase
from unittest.mock import patch

from apps.teams.services import create_team_with_owner

User = get_user_model()


class TeamModelTests(TestCase):
    def test_create_team_with_owner_generates_slug_and_admin_membership(self) -> None:
        owner = User.objects.create_user(
            email="owner@example.com",
            password="StrongPass123!",
            name="Owner User",
        )

        team = create_team_with_owner(created_by=owner, name="Backend Team", description="API development")

        self.assertEqual(team.slug, "backend-team")
        self.assertTrue(
            team.memberships.filter(
                user=owner,
                role="admin",
                status="active",
            ).exists()
        )

    @patch("apps.teams.services.log_team_action", side_effect=RuntimeError("audit offline"))
    def test_create_team_with_owner_still_succeeds_when_audit_logging_fails(self, _mock_log_team_action) -> None:
        owner = User.objects.create_user(
            email="resilient-owner@example.com",
            password="StrongPass123!",
            name="Owner User",
        )

        team = create_team_with_owner(created_by=owner, name="Resilient Team", description="Still creates")

        self.assertEqual(team.slug, "resilient-team")
        self.assertTrue(team.memberships.filter(user=owner, role="admin", status="active").exists())
