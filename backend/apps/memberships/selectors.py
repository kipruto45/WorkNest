from __future__ import annotations

from django.db.models import QuerySet

from apps.memberships.models import Membership, TeamInvitation, TeamInviteLink


def get_active_team_members(*, team) -> QuerySet[Membership]:
    return (
        Membership.objects.filter(team=team, status=Membership.Status.ACTIVE)
        .select_related("user", "team", "invited_by")
        .order_by("role", "user__name", "user__email")
    )


def get_team_member(*, team, user) -> Membership | None:
    return (
        Membership.objects.filter(team=team, user=user)
        .select_related("user", "team", "invited_by")
        .first()
    )


def get_team_member_by_id(*, team, membership_id) -> Membership | None:
    return (
        Membership.objects.filter(team=team, id=membership_id)
        .select_related("user", "team", "invited_by")
        .first()
    )


def get_pending_invitations(*, team) -> QuerySet[TeamInvitation]:
    return TeamInvitation.objects.filter(team=team, status=TeamInvitation.Status.PENDING).select_related(
        "team",
        "invited_by",
    )


def get_team_invitations(*, team) -> QuerySet[TeamInvitation]:
    return TeamInvitation.objects.filter(team=team).select_related("team", "invited_by")


def get_team_invitation_by_id(*, team, invitation_id) -> TeamInvitation | None:
    return (
        TeamInvitation.objects.filter(team=team, id=invitation_id)
        .select_related("team", "invited_by")
        .first()
    )


def get_invitation_by_token(*, token: str) -> TeamInvitation | None:
    return TeamInvitation.objects.filter(token=token).select_related("team", "invited_by").first()


def get_invitation_by_id(*, invitation_id) -> TeamInvitation | None:
    return TeamInvitation.objects.filter(id=invitation_id).select_related("team", "invited_by").first()


def get_team_invite_links(*, team) -> QuerySet[TeamInviteLink]:
    return TeamInviteLink.objects.filter(team=team).select_related("team", "created_by")


def get_team_invite_link_by_id(*, team, invite_link_id) -> TeamInviteLink | None:
    return (
        TeamInviteLink.objects.filter(team=team, id=invite_link_id)
        .select_related("team", "created_by")
        .first()
    )


def get_team_invite_link_by_token(*, token: str) -> TeamInviteLink | None:
    return TeamInviteLink.objects.filter(token=token).select_related("team", "created_by").first()


def get_invite_link_by_id(*, invite_link_id) -> TeamInviteLink | None:
    return TeamInviteLink.objects.filter(id=invite_link_id).select_related("team", "created_by").first()
