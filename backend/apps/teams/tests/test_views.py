from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.teams.models import Team

User = get_user_model()


class TeamViewTests(APITestCase):
    def authenticate(self, user) -> None:
        access = str(RefreshToken.for_user(user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

    def test_authenticated_user_can_create_team(self) -> None:
        user = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        self.authenticate(user)

        response = self.client.post(
            reverse("api_v1:teams:list-create"),
            {"name": "Platform Team", "description": "Owns the platform"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        team = Team.objects.get(id=response.data["data"]["id"])
        self.assertTrue(team.memberships.filter(user=user, role="admin", status="active").exists())
        self.assertEqual(response.data["data"]["member_count"], 1)
        self.assertEqual(response.data["data"]["my_membership"]["role"], "admin")
        self.assertEqual(response.data["message"], "Team created successfully.")

    def test_team_create_returns_clean_validation_errors(self) -> None:
        user = User.objects.create_user(email="owner-validation@example.com", password="StrongPass123!", name="Owner")
        self.authenticate(user)

        response = self.client.post(
            reverse("api_v1:teams:list-create"),
            {"name": " ", "description": "Owns validation"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], "This field may not be blank.")
        self.assertEqual(response.data["errors"]["name"], ["This field may not be blank."])

    def test_team_create_requires_authenticated_user(self) -> None:
        response = self.client.post(
            reverse("api_v1:teams:list-create"),
            {"name": "Secure Team", "description": "Protected"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data["success"])
        self.assertEqual(response.data["message"], "Authentication credentials were not provided.")

    def test_non_member_cannot_view_team(self) -> None:
        owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        outsider = User.objects.create_user(email="outsider@example.com", password="StrongPass123!", name="Outsider")
        self.authenticate(owner)
        create_response = self.client.post(
            reverse("api_v1:teams:list-create"),
            {"name": "Private Team", "description": ""},
            format="json",
        )
        team_id = create_response.data["data"]["id"]

        self.authenticate(outsider)
        detail_response = self.client.get(reverse("api_v1:teams:detail", args=[team_id]))

        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_archive_then_delete_team(self) -> None:
        owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        self.authenticate(owner)
        create_response = self.client.post(
            reverse("api_v1:teams:list-create"),
            {"name": "Archive Team", "description": ""},
            format="json",
        )
        team_id = create_response.data["data"]["id"]

        archive_response = self.client.post(reverse("api_v1:teams:archive", args=[team_id]))
        delete_response = self.client.delete(reverse("api_v1:teams:detail", args=[team_id]))

        self.assertEqual(archive_response.status_code, status.HTTP_200_OK)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_team_list_supports_search(self) -> None:
        owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        self.authenticate(owner)
        self.client.post(
            reverse("api_v1:teams:list-create"),
            {"name": "Growth Squad", "description": "Owns campaigns"},
            format="json",
        )
        self.client.post(
            reverse("api_v1:teams:list-create"),
            {"name": "Platform Team", "description": "Owns the backend"},
            format="json",
        )

        response = self.client.get(reverse("api_v1:teams:list-create"), {"search": "growth"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Growth Squad")

    def test_team_list_excludes_archived_by_default_and_can_filter_archived(self) -> None:
        owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        self.authenticate(owner)
        active_response = self.client.post(
            reverse("api_v1:teams:list-create"),
            {"name": "Active Team", "description": "Current workspace"},
            format="json",
        )
        archived_response = self.client.post(
            reverse("api_v1:teams:list-create"),
            {"name": "Archived Team", "description": "Old workspace"},
            format="json",
        )
        archived_team_id = archived_response.data["data"]["id"]
        self.client.post(reverse("api_v1:teams:archive", args=[archived_team_id]))

        default_list = self.client.get(reverse("api_v1:teams:list-create"))
        archived_list = self.client.get(reverse("api_v1:teams:list-create"), {"is_archived": "true"})

        self.assertEqual(default_list.status_code, status.HTTP_200_OK)
        self.assertEqual(archived_list.status_code, status.HTTP_200_OK)
        default_names = {item["name"] for item in default_list.data["data"]["results"]}
        archived_names = {item["name"] for item in archived_list.data["data"]["results"]}
        self.assertIn(active_response.data["data"]["name"], default_names)
        self.assertNotIn("Archived Team", default_names)
        self.assertIn("Archived Team", archived_names)
