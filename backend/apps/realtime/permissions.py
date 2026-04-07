from __future__ import annotations

from apps.memberships.models import Membership


def can_connect_user_channel(*, user) -> bool:
    return bool(user and getattr(user, "is_authenticated", False) and getattr(user, "is_active", True))


def is_active_team_member(*, user, team_id) -> bool:
    if not can_connect_user_channel(user=user):
        return False

    return Membership.objects.filter(
        team_id=team_id,
        user=user,
        status=Membership.Status.ACTIVE,
    ).exists()


def can_connect_team_channel(*, user, team_id) -> bool:
    return is_active_team_member(user=user, team_id=team_id)
