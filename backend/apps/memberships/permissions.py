from __future__ import annotations

from rest_framework.exceptions import PermissionDenied

from apps.memberships.models import Membership


def require_active_membership(*, membership: Membership | None) -> Membership:
    if membership is None or membership.status != Membership.Status.ACTIVE:
        raise PermissionDenied("You do not have access to this team.")
    return membership


def require_admin_membership(*, membership: Membership | None) -> Membership:
    membership = require_active_membership(membership=membership)
    if membership.role != Membership.Role.ADMIN:
        raise PermissionDenied("Only team admins can perform this action.")
    return membership
