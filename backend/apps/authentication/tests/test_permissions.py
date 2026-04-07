from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class AuthenticationPermissionTests(APITestCase):
    def test_logout_requires_authenticated_user(self) -> None:
        response = self.client.post(reverse("api_v1:authentication:logout"), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_profile_endpoint_requires_authenticated_user(self) -> None:
        response = self.client.get(reverse("api_v1:users:me"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
