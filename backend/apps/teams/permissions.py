from __future__ import annotations

from rest_framework.exceptions import PermissionDenied

from apps.memberships.models import Membership


def get_active_membership(*, team, user) -> Membership | None:
    if not user or not user.is_authenticated:
        return None
    return team.memberships.filter(user=user, status=Membership.Status.ACTIVE).first()


def require_team_member(*, team, user) -> Membership:
    membership = get_active_membership(team=team, user=user)
    if not membership:
        raise PermissionDenied("You do not have access to this team.")
    return membership


def require_team_admin(*, team, user) -> Membership:
    membership = require_team_member(team=team, user=user)
    if membership.role != Membership.Role.ADMIN:
        raise PermissionDenied("Only team admins can perform this action.")
    return membership


def can_manage_team_invites(*, team, user) -> bool:
    membership = get_active_membership(team=team, user=user)
    if not membership:
        return False
    if membership.role == Membership.Role.ADMIN:
        return True
    return membership.role == Membership.Role.MANAGER and bool(getattr(team, "allow_manager_invites", False))


def require_team_inviter(*, team, user) -> Membership:
    membership = require_team_member(team=team, user=user)
    if membership.role == Membership.Role.ADMIN:
        return membership
    if membership.role == Membership.Role.MANAGER and bool(getattr(team, "allow_manager_invites", False)):
        return membership
    raise PermissionDenied("You do not have permission to manage invitations for this team.")
