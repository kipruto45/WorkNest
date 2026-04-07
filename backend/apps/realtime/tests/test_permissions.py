from __future__ import annotations

from django.test import TestCase

from apps.memberships.models import Membership
from apps.realtime.permissions import can_connect_team_channel, can_connect_user_channel, is_active_team_member
from apps.realtime.tests.utils import RealtimeFixtureMixin


class RealtimePermissionTests(RealtimeFixtureMixin, TestCase):
    def test_active_authenticated_user_can_connect_personal_channel(self) -> None:
        self.assertTrue(can_connect_user_channel(user=self.member))

    def test_inactive_user_cannot_connect_personal_channel(self) -> None:
        self.member.is_active = False
        self.member.save(update_fields=["is_active"])

        self.assertFalse(can_connect_user_channel(user=self.member))

    def test_active_team_member_can_connect_team_channel(self) -> None:
        self.assertTrue(is_active_team_member(user=self.member, team_id=self.team.id))
        self.assertTrue(can_connect_team_channel(user=self.member, team_id=self.team.id))

    def test_removed_team_member_cannot_connect_team_channel(self) -> None:
        membership = Membership.objects.get(user=self.member, team=self.team)
        membership.status = Membership.Status.REMOVED
        membership.save(update_fields=["status", "updated_at"])

        self.assertFalse(can_connect_team_channel(user=self.member, team_id=self.team.id))

    def test_outsider_cannot_connect_foreign_team_channel(self) -> None:
        self.assertFalse(can_connect_team_channel(user=self.outsider, team_id=self.team.id))
