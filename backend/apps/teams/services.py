from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, log_team_action
from rest_framework.exceptions import ValidationError

from apps.memberships.models import Membership
from apps.teams.models import Team

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
    log_team_action(
        actor=created_by,
        action=AuditAction.TEAM_CREATED,
        team=team,
        metadata=build_audit_metadata(name=team.name, slug=team.slug, description=team.description),
    )
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
