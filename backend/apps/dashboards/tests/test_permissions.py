from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, APITestCase

from apps.dashboards.permissions import CanViewTeamAnalytics, CanViewTeamDashboard, IsActiveTeamMember
from apps.memberships.models import Membership
from apps.teams.models import Team

User = get_user_model()


class DashboardPermissionTests(APITestCase):
    def setUp(self) -> None:
        self.factory = APIRequestFactory()
        self.owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        self.member = User.objects.create_user(email="member@example.com", password="StrongPass123!", name="Member")
        self.manager = User.objects.create_user(email="manager@example.com", password="StrongPass123!", name="Manager")
        self.outsider = User.objects.create_user(email="outsider@example.com", password="StrongPass123!", name="Outsider")
        self.team = Team.objects.create(
            name="Analytics",
            slug="analytics",
            description="Analytics team",
            created_by=self.owner,
        )
        Membership.objects.create(
            team=self.team,
            user=self.member,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
        )
        Membership.objects.create(
            team=self.team,
            user=self.manager,
            role=Membership.Role.MANAGER,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
        )

    def test_active_member_has_team_dashboard_access(self) -> None:
        request = self.factory.get("/api/v1/dashboard/teams/test/summary/")
        request.user = self.member

        self.assertTrue(IsActiveTeamMember().has_object_permission(request, None, self.team))

    def test_cross_team_access_is_blocked(self) -> None:
        request = self.factory.get("/api/v1/dashboard/teams/test/summary/")
        request.user = self.outsider

        self.assertFalse(CanViewTeamDashboard().has_object_permission(request, None, self.team))

    def test_inactive_membership_is_blocked(self) -> None:
        membership = Membership.objects.get(team=self.team, user=self.member)
        membership.status = Membership.Status.REMOVED
        membership.save(update_fields=["status", "updated_at"])

        request = self.factory.get("/api/v1/dashboard/teams/test/summary/")
        request.user = self.member

        self.assertFalse(IsActiveTeamMember().has_object_permission(request, None, self.team))

    def test_unauthenticated_access_is_rejected(self) -> None:
        request = self.factory.get("/api/v1/dashboard/teams/test/summary/")
        request.user = type("Anonymous", (), {"is_authenticated": False})()

        self.assertFalse(IsActiveTeamMember().has_permission(request, None))

    def test_member_is_blocked_from_team_analytics_permission(self) -> None:
        request = self.factory.get("/api/v1/dashboard/teams/test/activity/")
        request.user = self.member

        self.assertFalse(CanViewTeamAnalytics().has_object_permission(request, None, self.team))

    def test_manager_has_team_analytics_permission(self) -> None:
        request = self.factory.get("/api/v1/dashboard/teams/test/activity/")
        request.user = self.manager

        self.assertTrue(CanViewTeamAnalytics().has_object_permission(request, None, self.team))
