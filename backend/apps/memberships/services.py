from __future__ import annotations

import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, log_membership_action
from apps.integrations.email.builders import _get_frontend_url
from apps.integrations.email.services import (
    queue_invitation_accepted_email,
    queue_invitation_reminder_email,
    queue_invitation_revoked_email,
    queue_role_changed_email,
    queue_team_invite_email,
)
from apps.integrations.models import EmailDelivery
from apps.memberships.models import Membership, TeamInvitation, TeamInviteLink
from apps.memberships.selectors import get_team_member
from apps.teams.permissions import can_manage_team_invites

logger = logging.getLogger(__name__)
User = get_user_model()


def _get_invitation_expiry():
    expiry_days = int(getattr(settings, "TEAM_INVITATION_EXPIRY_DAYS", 7))
    return timezone.now() + timedelta(days=expiry_days)


def _build_invitation_link(*, token: str) -> str:
    frontend_url = _get_frontend_url().rstrip("/")
    if frontend_url:
        return f"{frontend_url}/invitations/{token}"
    return f"/invitations/{token}"


def _build_invite_link_url(*, token: str) -> str:
    frontend_url = _get_frontend_url().rstrip("/")
    if frontend_url:
        return f"{frontend_url}/invite-links/{token}"
    return f"/invite-links/{token}"


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
    if invitation.team.is_personal:
        raise ValidationError({"invitation": ["Personal workspaces do not support invitations or shared memberships."]})


def _ensure_invitation_belongs_to_user(*, invitation: TeamInvitation, user) -> None:
    if invitation.email.lower() != user.email.lower():
        raise PermissionDenied("This invitation does not belong to the authenticated user.")


def _ensure_invitation_manageable(*, invitation: TeamInvitation, actor) -> None:
    if invitation.team.is_archived:
        raise ValidationError({"team": ["Archived teams cannot manage invitations."]})
    if invitation.team.is_personal:
        raise ValidationError({"team": ["Personal workspaces cannot send or manage invitations."]})
    if not can_manage_team_invites(team=invitation.team, user=actor):
        raise PermissionDenied("You do not have permission to manage invitations for this team.")


def _ensure_target_is_not_active_member(*, team, email: str) -> None:
    existing_user = _existing_user_for_email(email)
    if not existing_user:
        return
    existing_membership = get_team_member(team=team, user=existing_user)
    if existing_membership and existing_membership.status == Membership.Status.ACTIVE:
        raise ValidationError({"email": ["This user is already an active member of the team."]})


def _validate_email_invitation_role_for_actor(*, team, actor, role: str) -> None:
    membership = get_team_member(team=team, user=actor)
    if not membership or membership.status != Membership.Status.ACTIVE:
        raise PermissionDenied("You do not have permission to invite members to this team.")

    if membership.role == Membership.Role.ADMIN:
        return

    if membership.role != Membership.Role.MANAGER:
        raise PermissionDenied("You do not have permission to invite members to this team.")

    if role == Membership.Role.ADMIN:
        raise ValidationError({"role": ["Managers cannot invite admins."]})
    if role == Membership.Role.MANAGER and not bool(getattr(settings, "TEAM_ALLOW_MANAGER_ROLE_EMAIL_INVITES", False)):
        raise ValidationError({"role": ["Manager-role invitations are disabled for managers by policy."]})


def _validate_invite_link_role(*, role: str, actor) -> None:
    if role == Membership.Role.ADMIN and not bool(getattr(settings, "TEAM_ALLOW_ADMIN_ROLE_INVITE_LINKS", False)):
        raise ValidationError({"role": ["Admin invite links are disabled by policy."]})
    if role == Membership.Role.ADMIN and not bool(getattr(actor, "is_staff", False)):
        # Explicitly guard admin-role links to privileged actors only.
        raise ValidationError({"role": ["Only privileged admins can issue admin-role invite links."]})
    if role == Membership.Role.MANAGER and not bool(getattr(settings, "TEAM_ALLOW_MANAGER_ROLE_INVITE_LINKS", True)):
        raise ValidationError({"role": ["Manager invite links are disabled by policy."]})


def _ensure_invite_link_manageable(*, invite_link: TeamInviteLink, actor) -> None:
    if not can_manage_team_invites(team=invite_link.team, user=actor):
        raise PermissionDenied("You do not have permission to manage invite links for this team.")
    if invite_link.team.is_archived:
        raise ValidationError({"team": ["Archived teams cannot manage invite links."]})
    if invite_link.team.is_personal:
        raise ValidationError({"team": ["Personal workspaces cannot use invite links."]})


def _send_invitation_email(*, invitation: TeamInvitation) -> None:
    try:
        delivery = queue_team_invite_email(
            invitation=invitation,
            actor=invitation.invited_by,
            deliver_immediately=True,
        )
    except Exception:
        logger.exception(
            "team_invitation_email_queue_failed",
            extra={"team_id": str(invitation.team_id), "invitation_id": str(invitation.id)},
        )
        return

    if delivery.status in {EmailDelivery.Status.FAILED, EmailDelivery.Status.SKIPPED}:
        logger.warning(
            "team_invitation_email_delivery_failed",
            extra={
                "team_id": str(invitation.team_id),
                "invitation_id": str(invitation.id),
                "delivery_status": delivery.status,
            },
        )


def _send_invitation_reminder(*, invitation: TeamInvitation) -> None:
    try:
        delivery = queue_invitation_reminder_email(
            invitation=invitation,
            actor=invitation.invited_by,
            deliver_immediately=True,
        )
    except Exception:
        logger.exception(
            "team_invitation_reminder_queue_failed",
            extra={"team_id": str(invitation.team_id), "invitation_id": str(invitation.id)},
        )
        return

    if delivery.status in {EmailDelivery.Status.FAILED, EmailDelivery.Status.SKIPPED}:
        logger.warning(
            "team_invitation_reminder_delivery_failed",
            extra={
                "team_id": str(invitation.team_id),
                "invitation_id": str(invitation.id),
                "delivery_status": delivery.status,
            },
        )


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
    try:
        queue_invitation_accepted_email(invitation=invitation, recipient_user=invitation.invited_by, actor=actor)
    except Exception:
        logger.exception(
            "team_invitation_accepted_email_queue_failed",
            extra={"team_id": str(invitation.team_id), "invitation_id": str(invitation.id), "actor_id": str(actor.id)},
        )


def _notify_inviter_of_decline(*, invitation: TeamInvitation, actor) -> None:
    if invitation.invited_by_id is None or invitation.invited_by_id == actor.id:
        return
    from apps.notifications.services import notify_invitation_declined

    notify_invitation_declined(invitation=invitation, recipient_user=invitation.invited_by)


def refresh_team_invitation_state(*, invitation: TeamInvitation) -> TeamInvitation:
    return _mark_invitation_expired_if_needed(invitation)


def expire_team_invitations(*, team=None) -> int:
    queryset = TeamInvitation.objects.filter(
        status=TeamInvitation.Status.PENDING,
        expires_at__lte=timezone.now(),
    )
    if team is not None:
        queryset = queryset.filter(team=team)
    return queryset.update(status=TeamInvitation.Status.EXPIRED, updated_at=timezone.now())


@transaction.atomic
def invite_member_to_team(*, team, invited_by, email: str, role: str, custom_message: str = "") -> TeamInvitation:
    if team.is_archived:
        raise ValidationError({"team": ["Archived teams cannot send invitations."]})
    if team.is_personal:
        raise ValidationError({"team": ["Personal workspaces cannot invite members. Create a shared team workspace instead."]})
    if not can_manage_team_invites(team=team, user=invited_by):
        raise PermissionDenied("You do not have permission to invite members to this team.")

    normalized_email = email.strip().lower()
    normalized_message = custom_message.strip()
    inviter_email = str(getattr(invited_by, "email", "") or "").strip().lower()
    if inviter_email and inviter_email == normalized_email:
        raise ValidationError({"email": ["You are already part of this workspace. Invite another teammate instead."]})
    _validate_email_invitation_role_for_actor(team=team, actor=invited_by, role=role)
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


@transaction.atomic
def create_team_invite_link(
    *,
    team,
    actor,
    role: str = Membership.Role.MEMBER,
    label: str = "",
    expires_at=None,
    max_uses: int | None = None,
) -> TeamInviteLink:
    if team.is_archived:
        raise ValidationError({"team": ["Archived teams cannot create invite links."]})
    if team.is_personal:
        raise ValidationError({"team": ["Personal workspaces cannot use invite links."]})
    if not can_manage_team_invites(team=team, user=actor):
        raise PermissionDenied("You do not have permission to create invite links for this team.")

    membership = get_team_member(team=team, user=actor)
    actor_role = membership.role if membership else None
    if actor_role == Membership.Role.MANAGER and role != Membership.Role.MEMBER:
        raise ValidationError({"role": ["Managers can only generate member invite links."]})
    _validate_invite_link_role(role=role, actor=actor)

    if expires_at and expires_at <= timezone.now():
        raise ValidationError({"expires_at": ["Expiry must be in the future."]})

    invite_link = TeamInviteLink.objects.create(
        team=team,
        role=role,
        label=(label or "").strip(),
        created_by=actor,
        expires_at=expires_at,
        max_uses=max_uses,
    )

    log_membership_action(
        actor=actor,
        action=AuditAction.INVITE_LINK_CREATED,
        team=team,
        target=invite_link,
        metadata=build_audit_metadata(
            team_name=team.name,
            role=role,
            label=invite_link.label,
            expires_at=invite_link.expires_at,
            max_uses=max_uses,
            invite_link=_build_invite_link_url(token=invite_link.token),
        ),
    )
    return invite_link


@transaction.atomic
def revoke_team_invite_link(*, invite_link: TeamInviteLink, actor) -> TeamInviteLink:
    _ensure_invite_link_manageable(invite_link=invite_link, actor=actor)
    if invite_link.revoked_at:
        raise ValidationError({"invite_link": ["This invite link has already been revoked."]})

    invite_link.is_active = False
    invite_link.revoked_at = timezone.now()
    invite_link.save(update_fields=["is_active", "revoked_at", "updated_at"])

    log_membership_action(
        actor=actor,
        action=AuditAction.INVITE_LINK_REVOKED,
        team=invite_link.team,
        target=invite_link,
        metadata=build_audit_metadata(
            team_name=invite_link.team.name,
            role=invite_link.role,
            revoked_at=invite_link.revoked_at,
            label=invite_link.label,
        ),
    )
    return invite_link


@transaction.atomic
def regenerate_team_invite_link(*, invite_link: TeamInviteLink, actor) -> TeamInviteLink:
    _ensure_invite_link_manageable(invite_link=invite_link, actor=actor)

    invite_link.token = secrets.token_urlsafe(32)
    invite_link.is_active = True
    invite_link.revoked_at = None
    invite_link.current_uses = 0
    invite_link.last_used_at = None
    if invite_link.expires_at and invite_link.expires_at <= timezone.now():
        invite_link.expires_at = _get_invitation_expiry()
    invite_link.save(
        update_fields=[
            "token",
            "is_active",
            "revoked_at",
            "current_uses",
            "last_used_at",
            "expires_at",
            "updated_at",
        ]
    )

    log_membership_action(
        actor=actor,
        action=AuditAction.INVITE_LINK_REGENERATED,
        team=invite_link.team,
        target=invite_link,
        metadata=build_audit_metadata(
            team_name=invite_link.team.name,
            role=invite_link.role,
            label=invite_link.label,
            expires_at=invite_link.expires_at,
            max_uses=invite_link.max_uses,
            invite_link=_build_invite_link_url(token=invite_link.token),
        ),
    )
    return invite_link


def resolve_team_invite_link(*, invite_link: TeamInviteLink) -> TeamInviteLink:
    return invite_link


@transaction.atomic
def track_team_invite_link_copy(*, invite_link: TeamInviteLink, actor) -> TeamInviteLink:
    _ensure_invite_link_manageable(invite_link=invite_link, actor=actor)
    log_membership_action(
        actor=actor,
        action=AuditAction.INVITE_LINK_COPIED,
        team=invite_link.team,
        target=invite_link,
        metadata=build_audit_metadata(
            team_name=invite_link.team.name,
            role=invite_link.role,
            label=invite_link.label,
        ),
    )
    return invite_link


@transaction.atomic
def accept_team_invite_link(*, invite_link: TeamInviteLink, user) -> Membership:
    locked = TeamInviteLink.objects.select_for_update().select_related("team", "created_by").get(id=invite_link.id)
    if not locked.is_active or locked.revoked_at:
        raise ValidationError({"invite_link": ["This invite link has been revoked."]})
    if locked.team.is_archived:
        raise ValidationError({"invite_link": ["This team is archived and not accepting new members."]})
    if locked.team.is_personal:
        raise ValidationError({"invite_link": ["Personal workspaces do not support invite links."]})
    if locked.is_expired:
        raise ValidationError({"invite_link": ["This invite link has expired."]})
    if locked.max_uses is not None and locked.current_uses >= locked.max_uses:
        raise ValidationError({"invite_link": ["This invite link has reached its maximum uses."]})

    membership, created = Membership.objects.get_or_create(
        team=locked.team,
        user=user,
        defaults={
            "role": locked.role,
            "status": Membership.Status.ACTIVE,
            "invited_by": locked.created_by,
            "joined_at": timezone.now(),
        },
    )
    if not created and membership.status == Membership.Status.ACTIVE:
        raise ValidationError({"invite_link": ["You are already a member of this team."]})
    if not created:
        membership.role = locked.role
        membership.status = Membership.Status.ACTIVE
        membership.invited_by = locked.created_by
        membership.joined_at = timezone.now()
        membership.save(update_fields=["role", "status", "invited_by", "joined_at", "updated_at"])

    TeamInviteLink.objects.filter(id=locked.id).update(
        current_uses=F("current_uses") + 1,
        last_used_at=timezone.now(),
        updated_at=timezone.now(),
    )
    locked.refresh_from_db(fields=["current_uses", "last_used_at", "updated_at"])

    log_membership_action(
        actor=user,
        action=AuditAction.INVITE_LINK_USED,
        team=locked.team,
        target=locked,
        metadata=build_audit_metadata(
            team_name=locked.team.name,
            role=locked.role,
            current_uses=locked.current_uses,
            max_uses=locked.max_uses,
            label=locked.label,
        ),
    )
    log_membership_action(
        actor=user,
        action=AuditAction.MEMBERSHIP_CREATED_FROM_INVITE_LINK,
        team=locked.team,
        membership=membership,
        target=locked,
        metadata=build_audit_metadata(
            team_name=locked.team.name,
            role=membership.role,
            user_id=user.id,
            user_email=user.email,
            label=locked.label,
        ),
    )
    return membership


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
    try:
        queue_invitation_revoked_email(invitation=invitation, actor=actor)
    except Exception:
        logger.exception(
            "team_invitation_revoked_email_queue_failed",
            extra={"team_id": str(invitation.team_id), "invitation_id": str(invitation.id), "actor_id": str(actor.id)},
        )

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
    _validate_email_invitation_role_for_actor(team=invitation.team, actor=actor, role=new_role)

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
