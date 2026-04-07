from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, create_audit_log, log_team_action
from rest_framework.exceptions import ValidationError

from apps.memberships.models import Membership
from apps.notifications.constants import NotificationType
from apps.notifications.services import create_bulk_notifications
from apps.teams.models import FavoriteTeam, RecentTeamVisit, Team, TeamAnnouncement

logger = logging.getLogger(__name__)


def generate_unique_team_slug(*, name: str) -> str:
    base_slug = slugify(name)[:170] or "team"
    slug = base_slug
    counter = 2
    while Team.objects.filter(slug=slug).exists():
        suffix = f"-{counter}"
        slug = f"{base_slug[:180 - len(suffix)]}{suffix}"
        counter += 1
    return slug


@transaction.atomic
def create_team_with_owner(*, created_by, name: str, description: str = "", allow_manager_invites: bool = False) -> Team:
    team = Team.objects.create(
        name=name.strip(),
        slug=generate_unique_team_slug(name=name),
        description=description.strip(),
        allow_manager_invites=allow_manager_invites,
        created_by=created_by,
    )
    Membership.objects.create(
        team=team,
        user=created_by,
        role=Membership.Role.ADMIN,
        status=Membership.Status.ACTIVE,
        invited_by=created_by,
        joined_at=timezone.now(),
    )
    try:
        log_team_action(
            actor=created_by,
            action=AuditAction.TEAM_CREATED,
            team=team,
            metadata=build_audit_metadata(name=team.name, slug=team.slug, description=team.description),
        )
    except Exception:  # pragma: no cover - defensive production fallback
        logger.exception("team_create_audit_failed", extra={"team_id": str(team.id), "actor_id": str(created_by.id)})
    logger.info("team_created", extra={"team_id": str(team.id), "actor_id": str(created_by.id)})
    return team


@transaction.atomic
def update_team(*, team: Team, actor, **changes) -> Team:
    updated_fields: list[str] = []
    changed_values: dict[str, dict] = {}
    for field in ("name", "description", "allow_manager_invites"):
        if field in changes:
            value = changes[field]
            old_value = getattr(team, field)
            setattr(team, field, value.strip() if isinstance(value, str) else value)
            updated_fields.append(field)
            changed_values[field] = {"old": old_value, "new": getattr(team, field)}
    if updated_fields:
        team.save(update_fields=updated_fields + ["updated_at"])
        log_team_action(
            actor=actor,
            action=AuditAction.TEAM_UPDATED,
            team=team,
            metadata=build_audit_metadata(updated_fields=updated_fields, changes=changed_values),
        )
        logger.info(
            "team_updated",
            extra={"team_id": str(team.id), "actor_id": str(actor.id), "fields": updated_fields},
        )
    return team


@transaction.atomic
def archive_team(*, team: Team, actor) -> Team:
    if not team.is_archived:
        team.is_archived = True
        team.archived_at = timezone.now()
        team.save(update_fields=["is_archived", "archived_at", "updated_at"])
        log_team_action(
            actor=actor,
            action=AuditAction.TEAM_ARCHIVED,
            team=team,
            metadata=build_audit_metadata(name=team.name, archived_at=team.archived_at),
        )
        logger.info("team_archived", extra={"team_id": str(team.id), "actor_id": str(actor.id)})
    return team


@transaction.atomic
def delete_team_if_allowed(*, team: Team, actor) -> None:
    if not team.is_archived:
        raise ValidationError({"team": ["Archive the team before deleting it permanently."]})
    log_team_action(
        actor=actor,
        action=AuditAction.TEAM_DELETED,
        team=team,
        metadata=build_audit_metadata(name=team.name, slug=team.slug),
    )
    logger.info("team_deleted", extra={"team_id": str(team.id), "actor_id": str(actor.id)})
    team.delete()


@transaction.atomic
def create_team_announcement(*, team: Team, actor, title: str, content: str, pinned_until=None) -> TeamAnnouncement:
    announcement = TeamAnnouncement.objects.create(
        team=team,
        title=title.strip(),
        content=content.strip(),
        pinned_until=pinned_until,
        published_by=actor,
    )
    log_team_action(
        actor=actor,
        action=AuditAction.TEAM_ANNOUNCEMENT_CREATED,
        team=team,
        target=announcement,
        metadata=build_audit_metadata(title=announcement.title, pinned_until=announcement.pinned_until),
    )

    recipients = [
        membership.user
        for membership in team.memberships.select_related("user").filter(status=Membership.Status.ACTIVE)
        if membership.user_id != actor.id
    ]
    if recipients:
        create_bulk_notifications(
            users=recipients,
            notification_type=NotificationType.TEAM_ANNOUNCEMENT,
            title=announcement.title,
            message_builder=lambda _user: announcement.content,
            actor=actor,
            team=team,
            metadata_builder=lambda _user: {"announcement_id": str(announcement.id), "team_id": str(team.id)},
            target_type="team_announcement",
            target_id=announcement.id,
        )
    return announcement


@transaction.atomic
def update_team_announcement(*, announcement: TeamAnnouncement, actor, title: str | None = None, content: str | None = None, pinned_until=...):
    changes = {}
    if title is not None:
        changes["title"] = {"old": announcement.title, "new": title.strip()}
        announcement.title = title.strip()
    if content is not None:
        changes["content"] = {"old": announcement.content, "new": content.strip()}
        announcement.content = content.strip()
    if pinned_until is not ...:
        changes["pinned_until"] = {"old": announcement.pinned_until, "new": pinned_until}
        announcement.pinned_until = pinned_until
    if changes:
        announcement.save()
        log_team_action(
            actor=actor,
            action=AuditAction.TEAM_ANNOUNCEMENT_UPDATED,
            team=announcement.team,
            target=announcement,
            metadata=build_audit_metadata(changes=changes),
        )
    return announcement


def touch_recent_team(*, team: Team, user) -> None:
    RecentTeamVisit.objects.update_or_create(
        user=user,
        team=team,
        defaults={"last_accessed_at": timezone.now()},
    )


@transaction.atomic
def toggle_team_pin(*, team: Team, user) -> bool:
    favorite, created = FavoriteTeam.objects.get_or_create(team=team, user=user)
    if created:
        create_audit_log(
            actor=user,
            action=AuditAction.TEAM_PINNED,
            team=team,
            target=team,
            metadata=build_audit_metadata(team_id=team.id),
        )
        return True
    favorite.delete()
    create_audit_log(
        actor=user,
        action=AuditAction.TEAM_UNPINNED,
        team=team,
        target=team,
        metadata=build_audit_metadata(team_id=team.id),
    )
    return False
