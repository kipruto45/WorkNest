from django.test import TestCase

from apps.teams.serializers import TeamCreateSerializer


class TeamSerializerTests(TestCase):
    def test_team_create_serializer_rejects_short_name(self) -> None:
        serializer = TeamCreateSerializer(data={"name": "A", "description": "Test"})

        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)
