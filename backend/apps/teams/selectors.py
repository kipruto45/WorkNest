from __future__ import annotations

from django.db.models import Count, Prefetch, Q

from apps.memberships.models import Membership
from apps.teams.models import FavoriteTeam, RecentTeamVisit, Team, TeamAnnouncement


def get_user_teams(*, user, include_archived: bool | None = False):
    active_membership_queryset = Membership.objects.filter(
        user=user,
        status=Membership.Status.ACTIVE,
    )
    queryset = Team.objects.filter(
        memberships__user=user,
        memberships__status=Membership.Status.ACTIVE,
    )
    if include_archived is True:
        queryset = queryset.filter(is_archived=True)
    elif include_archived is False:
        queryset = queryset.filter(is_archived=False)
    return (
        queryset
        .select_related("created_by")
        .prefetch_related(
            Prefetch(
                "memberships",
                queryset=active_membership_queryset,
                to_attr="active_memberships_for_request_user",
            ),
        )
        .annotate(
            member_count=Count(
                "memberships",
                filter=Q(memberships__status=Membership.Status.ACTIVE),
                distinct=True,
            )
        )
        .distinct()
        .order_by("name", "-created_at")
    )


def get_team_by_id_for_user(*, team_id, user, include_archived: bool | None = False):
    return get_user_teams(user=user, include_archived=include_archived).filter(id=team_id).first()


def get_team_announcements(*, team: Team):
    return TeamAnnouncement.objects.select_related("published_by").filter(team=team, is_active=True).order_by("-created_at")


def get_pinned_teams(*, user):
    return FavoriteTeam.objects.select_related("team", "team__created_by").filter(user=user).order_by("-updated_at")


def get_recent_team_visits(*, user):
    return RecentTeamVisit.objects.select_related("team", "team__created_by").filter(user=user).order_by("-last_accessed_at")
