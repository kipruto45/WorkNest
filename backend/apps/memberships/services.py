from __future__ import annotations

import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, log_membership_action
from apps.integrations.email.services import (
    queue_invitation_accepted_email,
    queue_invitation_reminder_email,
    queue_invitation_revoked_email,
    queue_role_changed_email,
    queue_team_invite_email,
)
from apps.memberships.models import Membership, TeamInvitation
from apps.memberships.selectors import get_team_member
from apps.teams.permissions import can_manage_team_invites

logger = logging.getLogger(__name__)
User = get_user_model()


def _get_invitation_expiry():
    expiry_days = int(getattr(settings, "TEAM_INVITATION_EXPIRY_DAYS", 7))
    return timezone.now() + timedelta(days=expiry_days)


def _build_invitation_link(*, token: str) -> str:
    frontend_url = getattr(settings, "FRONTEND_URL", "").rstrip("/")
    if frontend_url:
        return f"{frontend_url}/invitations/{token}"
    return f"/invitations/{token}"


def _existing_user_for_email(email: str):
    return User.objects.filter(email=email).first()


def _mark_invitation_expired_if_needed(invitation: TeamInvitation) -> TeamInvitation:
    if invitation.status == TeamInvitation.Status.PENDING and invitation.is_expired:
        TeamInvitation.objects.filter(pk=invitation.pk).update(
            status=TeamInvitation.Status.EXPIRED,
            updated_at=timezone.now(),
        )
        invitation.status = TeamInvitation.Status.EXPIRED
    return invitation


def _ensure_team_accepts_invites(*, invitation: TeamInvitation) -> None:
    if invitation.team.is_archived:
        raise ValidationError({"invitation": ["This team is archived, so the invitation can no longer be accepted."]})


def _ensure_invitation_belongs_to_user(*, invitation: TeamInvitation, user) -> None:
    if invitation.email.lower() != user.email.lower():
        raise PermissionDenied("This invitation does not belong to the authenticated user.")


def _ensure_invitation_manageable(*, invitation: TeamInvitation, actor) -> None:
    if invitation.team.is_archived:
        raise ValidationError({"team": ["Archived teams cannot manage invitations."]})
    if not can_manage_team_invites(team=invitation.team, user=actor):
        raise PermissionDenied("You do not have permission to manage invitations for this team.")


def _ensure_target_is_not_active_member(*, team, email: str) -> None:
    existing_user = _existing_user_for_email(email)
    if not existing_user:
        return
    existing_membership = get_team_member(team=team, user=existing_user)
    if existing_membership and existing_membership.status == Membership.Status.ACTIVE:
        raise ValidationError({"email": ["This user is already an active member of the team."]})


def _send_invitation_email(*, invitation: TeamInvitation) -> None:
    queue_team_invite_email(invitation=invitation, actor=invitation.invited_by)


def _send_invitation_reminder(*, invitation: TeamInvitation) -> None:
    queue_invitation_reminder_email(invitation=invitation, actor=invitation.invited_by)


def _notify_existing_invitee(*, invitation: TeamInvitation) -> None:
    existing_user = _existing_user_for_email(invitation.email)
    if not existing_user:
        return
    from apps.notifications.services import notify_team_invite

    notify_team_invite(invitation=invitation, recipient_user=existing_user)


def _notify_inviter_of_acceptance(*, invitation: TeamInvitation, actor) -> None:
    if invitation.invited_by_id is None or invitation.invited_by_id == actor.id:
        return
    from apps.notifications.services import notify_invitation_accepted

    notify_invitation_accepted(invitation=invitation, recipient_user=invitation.invited_by)
    queue_invitation_accepted_email(invitation=invitation, recipient_user=invitation.invited_by, actor=actor)


def _notify_inviter_of_decline(*, invitation: TeamInvitation, actor) -> None:
    if invitation.invited_by_id is None or invitation.invited_by_id == actor.id:
        return
    from apps.notifications.services import notify_invitation_declined

    notify_invitation_declined(invitation=invitation, recipient_user=invitation.invited_by)


@transaction.atomic
def invite_member_to_team(*, team, invited_by, email: str, role: str, custom_message: str = "") -> TeamInvitation:
    if team.is_archived:
        raise ValidationError({"team": ["Archived teams cannot send invitations."]})
    if not can_manage_team_invites(team=team, user=invited_by):
        raise PermissionDenied("You do not have permission to invite members to this team.")

    normalized_email = email.strip().lower()
    normalized_message = custom_message.strip()
    _ensure_target_is_not_active_member(team=team, email=normalized_email)

    pending_invitation = TeamInvitation.objects.filter(
        team=team,
        email=normalized_email,
        status=TeamInvitation.Status.PENDING,
        expires_at__gt=timezone.now(),
    ).first()
    if pending_invitation:
        raise ValidationError({"email": ["A pending invitation already exists for this email. Use resend instead."]})

    invitation = TeamInvitation.objects.create(
        team=team,
        email=normalized_email,
        role=role,
        token=secrets.token_urlsafe(32),
        invited_by=invited_by,
        expires_at=_get_invitation_expiry(),
        custom_message=normalized_message,
    )

    _send_invitation_email(invitation=invitation)
    _notify_existing_invitee(invitation=invitation)

    logger.info(
        "team_invitation_created",
        extra={"team_id": str(team.id), "actor_id": str(invited_by.id), "email": normalized_email, "role": role},
    )
    log_membership_action(
        actor=invited_by,
        action=AuditAction.MEMBER_INVITED,
        invitation=invitation,
        team=team,
        metadata=build_audit_metadata(
            email=normalized_email,
            role=role,
            custom_message=normalized_message,
            expires_at=invitation.expires_at,
            team_name=team.name,
        ),
    )
    return invitation


def accept_team_invitation(*, invitation: TeamInvitation, user):
    invitation = _mark_invitation_expired_if_needed(invitation)
    _ensure_team_accepts_invites(invitation=invitation)

    if invitation.status != TeamInvitation.Status.PENDING:
        raise ValidationError({"invitation": ["This invitation is no longer valid."]})
    _ensure_invitation_belongs_to_user(invitation=invitation, user=user)

    with transaction.atomic():
        membership, created = Membership.objects.get_or_create(
            team=invitation.team,
            user=user,
            defaults={
                "role": invitation.role,
                "status": Membership.Status.ACTIVE,
                "invited_by": invitation.invited_by,
                "joined_at": timezone.now(),
            },
        )

        if not created and membership.status == Membership.Status.ACTIVE:
            raise ValidationError({"invitation": ["You are already an active member of this team."]})

        if not created:
            membership.role = invitation.role
            membership.status = Membership.Status.ACTIVE
            membership.invited_by = invitation.invited_by
            membership.joined_at = timezone.now()
            membership.save(update_fields=["role", "status", "invited_by", "joined_at", "updated_at"])

        invitation.status = TeamInvitation.Status.ACCEPTED
        invitation.accepted_at = timezone.now()
        invitation.declined_at = None
        invitation.revoked_at = None
        invitation.save(update_fields=["status", "accepted_at", "declined_at", "revoked_at", "updated_at"])

    logger.info(
        "team_invitation_accepted",
        extra={"team_id": str(invitation.team.id), "user_id": str(user.id), "invitation_id": str(invitation.id)},
    )
    log_membership_action(
        actor=user,
        action=AuditAction.INVITATION_ACCEPTED,
        invitation=invitation,
        team=invitation.team,
        metadata=build_audit_metadata(
            email=invitation.email,
            role=invitation.role,
            team_name=invitation.team.name,
            accepted_at=invitation.accepted_at,
        ),
    )
    _notify_inviter_of_acceptance(invitation=invitation, actor=user)
    return membership


def decline_team_invitation(*, invitation: TeamInvitation, user) -> TeamInvitation:
    invitation = _mark_invitation_expired_if_needed(invitation)
    if invitation.status != TeamInvitation.Status.PENDING:
        raise ValidationError({"invitation": ["This invitation is no longer valid."]})
    _ensure_invitation_belongs_to_user(invitation=invitation, user=user)

    with transaction.atomic():
        invitation.status = TeamInvitation.Status.DECLINED
        invitation.declined_at = timezone.now()
        invitation.save(update_fields=["status", "declined_at", "updated_at"])

    logger.info(
        "team_invitation_declined",
        extra={"team_id": str(invitation.team.id), "user_id": str(user.id), "invitation_id": str(invitation.id)},
    )
    log_membership_action(
        actor=user,
        action=AuditAction.INVITATION_DECLINED,
        invitation=invitation,
        team=invitation.team,
        metadata=build_audit_metadata(
            email=invitation.email,
            role=invitation.role,
            team_name=invitation.team.name,
            declined_at=invitation.declined_at,
        ),
    )
    _notify_inviter_of_decline(invitation=invitation, actor=user)
    return invitation


@transaction.atomic
def resend_team_invitation(*, invitation: TeamInvitation, actor) -> TeamInvitation:
    invitation = _mark_invitation_expired_if_needed(invitation)
    _ensure_invitation_manageable(invitation=invitation, actor=actor)
    if invitation.status == TeamInvitation.Status.ACCEPTED:
        raise ValidationError({"invitation": ["Accepted invitations cannot be resent."]})

    _ensure_target_is_not_active_member(team=invitation.team, email=invitation.email)

    invitation.token = secrets.token_urlsafe(32)
    invitation.status = TeamInvitation.Status.PENDING
    invitation.expires_at = _get_invitation_expiry()
    invitation.accepted_at = None
    invitation.declined_at = None
    invitation.revoked_at = None
    invitation.save(
        update_fields=[
            "token",
            "status",
            "expires_at",
            "accepted_at",
            "declined_at",
            "revoked_at",
            "updated_at",
        ]
    )

    _send_invitation_reminder(invitation=invitation)
    _notify_existing_invitee(invitation=invitation)

    log_membership_action(
        actor=actor,
        action=AuditAction.INVITATION_RESENT,
        invitation=invitation,
        team=invitation.team,
        metadata=build_audit_metadata(
            email=invitation.email,
            role=invitation.role,
            expires_at=invitation.expires_at,
            team_name=invitation.team.name,
        ),
    )
    return invitation


@transaction.atomic
def revoke_team_invitation(*, invitation: TeamInvitation, actor) -> TeamInvitation:
    invitation = _mark_invitation_expired_if_needed(invitation)
    _ensure_invitation_manageable(invitation=invitation, actor=actor)
    if invitation.status == TeamInvitation.Status.ACCEPTED:
        raise ValidationError({"invitation": ["Accepted invitations cannot be revoked."]})
    if invitation.status == TeamInvitation.Status.REVOKED:
        raise ValidationError({"invitation": ["This invitation has already been revoked."]})

    invitation.status = TeamInvitation.Status.REVOKED
    invitation.revoked_at = timezone.now()
    invitation.save(update_fields=["status", "revoked_at", "updated_at"])
    queue_invitation_revoked_email(invitation=invitation, actor=actor)

    log_membership_action(
        actor=actor,
        action=AuditAction.INVITATION_REVOKED,
        invitation=invitation,
        team=invitation.team,
        metadata=build_audit_metadata(
            email=invitation.email,
            role=invitation.role,
            revoked_at=invitation.revoked_at,
            team_name=invitation.team.name,
        ),
    )
    return invitation


@transaction.atomic
def update_team_invitation_role(*, invitation: TeamInvitation, actor, new_role: str) -> TeamInvitation:
    invitation = _mark_invitation_expired_if_needed(invitation)
    _ensure_invitation_manageable(invitation=invitation, actor=actor)
    if invitation.status == TeamInvitation.Status.ACCEPTED:
        raise ValidationError({"invitation": ["Accepted invitations cannot be changed."]})
    if invitation.role == new_role:
        raise ValidationError({"role": ["The invitation already has this role."]})

    old_role = invitation.role
    invitation.role = new_role
    invitation.save(update_fields=["role", "updated_at"])
    _send_invitation_reminder(invitation=invitation)

    log_membership_action(
        actor=actor,
        action=AuditAction.INVITATION_ROLE_UPDATED,
        invitation=invitation,
        team=invitation.team,
        metadata=build_audit_metadata(
            email=invitation.email,
            old_role=old_role,
            new_role=new_role,
            team_name=invitation.team.name,
        ),
    )
    return invitation


@transaction.atomic
def change_member_role(*, team, actor, membership: Membership, new_role: str) -> Membership:
    if membership.status != Membership.Status.ACTIVE:
        raise ValidationError({"membership": ["Only active members can have their role updated."]})
    if membership.role == new_role:
        raise ValidationError({"role": ["The member already has this role."]})
    if membership.role == Membership.Role.ADMIN and new_role != Membership.Role.ADMIN and _count_active_admins(team=team) <= 1:
        raise ValidationError({"role": ["You cannot demote the last active admin."]})

    old_role = membership.role
    membership.role = new_role
    membership.save(update_fields=["role", "updated_at"])
    queue_role_changed_email(membership=membership, actor=actor, old_role=old_role, new_role=new_role)
    log_membership_action(
        actor=actor,
        action=AuditAction.MEMBER_ROLE_CHANGED,
        membership=membership,
        team=team,
        metadata=build_audit_metadata(
            member_id=membership.user_id,
            member_email=membership.user.email,
            old_role=old_role,
            new_role=new_role,
        ),
    )
    logger.info(
        "team_member_role_changed",
        extra={
            "team_id": str(team.id),
            "actor_id": str(actor.id),
            "membership_id": str(membership.id),
            "new_role": new_role,
        },
    )
    return membership


def _count_active_admins(*, team) -> int:
    return team.memberships.filter(role=Membership.Role.ADMIN, status=Membership.Status.ACTIVE).count()


@transaction.atomic
def remove_member_from_team(*, team, actor, membership: Membership) -> Membership:
    if membership.status != Membership.Status.ACTIVE:
        raise ValidationError({"membership": ["This membership is not active."]})
    if membership.role == Membership.Role.ADMIN and _count_active_admins(team=team) <= 1:
        raise ValidationError({"membership": ["You cannot remove the last active admin."]})

    removed_role = membership.role
    removed_user_id = membership.user_id
    removed_user_email = membership.user.email
    membership.status = Membership.Status.REMOVED
    membership.save(update_fields=["status", "updated_at"])
    log_membership_action(
        actor=actor,
        action=AuditAction.MEMBER_REMOVED,
        membership=membership,
        team=team,
        metadata=build_audit_metadata(member_id=removed_user_id, member_email=removed_user_email, role=removed_role),
    )
    logger.info(
        "team_member_removed",
        extra={
            "team_id": str(team.id),
            "actor_id": str(actor.id),
            "membership_id": str(membership.id),
        },
    )
    return membership
