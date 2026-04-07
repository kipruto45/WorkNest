from django.contrib.auth import get_user_model
from django.test import TestCase

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
