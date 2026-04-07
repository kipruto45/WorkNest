from __future__ import annotations

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, log_task_action
from rest_framework.exceptions import ValidationError

from apps.memberships.models import Membership
from apps.realtime.services import (
    send_task_archived_event,
    send_task_assignment_event,
    send_task_created_event,
    send_task_deleted_event,
    send_task_status_changed_event,
    send_task_update_event,
)
from apps.tasks.models import Task
from apps.teams.models import Team
from apps.users.models import User

UNSET = object()


def _get_task_position(*, team: Team, status: str) -> int:
    max_position = (
        Task.objects.filter(team=team, status=status, is_archived=False).aggregate(max_position=Max("position"))[
            "max_position"
        ]
        or 0
    )
    return max_position + 1


def validate_task_assignment(*, team: Team, user: User | None) -> User | None:
    if user is None:
        return None
    if not user.is_active:
        raise ValidationError({"assigned_to": ["Selected user is inactive."]})
    membership = Membership.objects.filter(team=team, user=user, status=Membership.Status.ACTIVE).first()
    if not membership:
        raise ValidationError({"assigned_to": ["Selected user is not a member of this team."]})
    return user


def _sync_completion_metadata(*, task: Task, previous_status: str, new_status: str, changed_by: User | None) -> None:
    if previous_status == new_status:
        return
    task.last_status_changed_at = timezone.now()
    task.last_status_changed_by = changed_by
    if new_status == Task.Status.DONE:
        task.completed_at = timezone.now()
    elif previous_status == Task.Status.DONE:
        task.completed_at = None


@transaction.atomic
def create_task(
    *,
    team: Team,
    title: str,
    description: str = "",
    status: str = Task.Status.TODO,
    priority: str = Task.Priority.MEDIUM,
    due_date=None,
    created_by: User,
    assigned_to: User | None = None,
    position: int | None = None,
) -> Task:
    if team.is_archived:
        raise ValidationError({"team_id": ["Archived teams cannot receive new tasks."]})
    assigned_user = validate_task_assignment(team=team, user=assigned_to)
    task = Task.objects.create(
        team=team,
        title=title,
        description=description,
        status=status,
        priority=priority,
        due_date=due_date,
        assigned_to=assigned_user,
        created_by=created_by,
        position=position if position is not None else _get_task_position(team=team, status=status),
    )
    if status == Task.Status.DONE:
        task.completed_at = timezone.now()
        task.last_status_changed_at = timezone.now()
        task.last_status_changed_by = created_by
        task.save(update_fields=["completed_at", "last_status_changed_at", "last_status_changed_by"])

    log_task_action(
        actor=created_by,
        action=AuditAction.TASK_CREATED,
        task=task,
        metadata=build_audit_metadata(
            title=task.title,
            status=task.status,
            priority=task.priority,
            assigned_to_id=task.assigned_to_id,
            due_date=task.due_date,
        ),
    )
    transaction.on_commit(lambda: send_task_created_event(task=task))

    if assigned_user and created_by and assigned_user.id != created_by.id:
        from apps.notifications.services import notify_task_assignment
        from apps.integrations.email.services import send_task_assigned_email
        from django.conf import settings

        transaction.on_commit(lambda: notify_task_assignment(task=task, actor=created_by))
        transaction.on_commit(lambda: send_task_assignment_event(task=task, actor=created_by))
        
        email_enabled = getattr(settings, 'NOTIFICATION_EMAIL_ENABLED', True)
        notify_types = getattr(settings, 'NOTIFICATION_EMAIL_TYPES', 'task_assigned,mentioned_in_comment,deadline_approaching,comment_posted')
        if email_enabled and 'task_assigned' in notify_types:
            try:
                transaction.on_commit(
                    lambda task=task, created_by=created_by: send_task_assigned_email(task=task, assigner=created_by, assignee=assigned_user)
                )
            except Exception:
                pass
    return task


@transaction.atomic
def update_task(
    *,
    task: Task,
    actor,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    due_date=UNSET,
    position: int | None = None,
) -> Task:
    changed_fields: dict[str, dict] = {}
    if title is not None:
        changed_fields["title"] = {"old": task.title, "new": title}
        task.title = title
    if description is not None:
        changed_fields["description"] = {"old": task.description, "new": description}
        task.description = description
    if priority is not None:
        changed_fields["priority"] = {"old": task.priority, "new": priority}
        task.priority = priority
    if due_date is not UNSET:
        changed_fields["due_date"] = {"old": task.due_date, "new": due_date}
        task.due_date = due_date
    if position is not None:
        changed_fields["position"] = {"old": task.position, "new": position}
        task.position = position
    task.save()
    if changed_fields:
        log_task_action(
            actor=actor,
            action=AuditAction.TASK_UPDATED,
            task=task,
            metadata=build_audit_metadata(updated_fields=list(changed_fields.keys()), changes=changed_fields),
        )
    transaction.on_commit(lambda: send_task_update_event(task=task))
    return task


@transaction.atomic
def delete_task(*, task: Task, actor=None) -> None:
    log_task_action(
        actor=actor,
        action=AuditAction.TASK_DELETED,
        task=task,
        metadata=build_audit_metadata(title=task.title, status=task.status, assigned_to_id=task.assigned_to_id),
    )
    transaction.on_commit(lambda: send_task_deleted_event(task=task))
    task.delete()


@transaction.atomic
def archive_task(*, task: Task, actor: User | None = None) -> Task:
    task.is_archived = True
    task.archived_at = timezone.now()
    task.save(update_fields=["is_archived", "archived_at", "updated_at"])
    log_task_action(
        actor=actor,
        action=AuditAction.TASK_ARCHIVED,
        task=task,
        metadata=build_audit_metadata(title=task.title, archived_at=task.archived_at),
    )
    transaction.on_commit(lambda: send_task_archived_event(task=task))
    return task


@transaction.atomic
def assign_task(*, task: Task, user: User | None, actor: User | None = None) -> Task:
    previous_assignee_id = task.assigned_to_id
    task.assigned_to = validate_task_assignment(team=task.team, user=user)
    task.save(update_fields=["assigned_to", "updated_at"])
    if task.assigned_to_id != previous_assignee_id:
        log_task_action(
            actor=actor,
            action=AuditAction.TASK_ASSIGNED,
            task=task,
            metadata=build_audit_metadata(
                old_assignee_id=previous_assignee_id,
                new_assignee_id=task.assigned_to_id,
                task_title=task.title,
            ),
        )
    if task.assigned_to_id and task.assigned_to_id != previous_assignee_id:
        from apps.notifications.services import notify_task_assignment
        from apps.integrations.email.services import send_task_assigned_email
        from django.conf import settings

        transaction.on_commit(lambda: notify_task_assignment(task=task, actor=actor))
        transaction.on_commit(lambda: send_task_assignment_event(task=task, actor=actor))
        
        if actor and task.assigned_to and actor.id != task.assigned_to.id:
            email_enabled = getattr(settings, 'NOTIFICATION_EMAIL_ENABLED', True)
            notify_types = getattr(settings, 'NOTIFICATION_EMAIL_TYPES', 'task_assigned,mentioned_in_comment,deadline_approaching,comment_posted')
            if email_enabled and 'task_assigned' in notify_types:
                try:
                    transaction.on_commit(
                        lambda: send_task_assigned_email(task=task, assigner=actor, assignee=task.assigned_to)
                    )
                except Exception:
                    pass
    else:
        transaction.on_commit(lambda: send_task_update_event(task=task))
    return task


@transaction.atomic
def change_task_status(*, task: Task, new_status: str, changed_by: User | None = None) -> Task:
    previous_status = task.status
    if previous_status != new_status:
        task.status = new_status
        task.position = _get_task_position(team=task.team, status=new_status)
        _sync_completion_metadata(
            task=task,
            previous_status=previous_status,
            new_status=new_status,
            changed_by=changed_by,
        )
        task.save()
        log_task_action(
            actor=changed_by,
            action=AuditAction.TASK_STATUS_CHANGED,
            task=task,
            metadata=build_audit_metadata(old_status=previous_status, new_status=new_status, task_title=task.title),
        )
        transaction.on_commit(
            lambda: send_task_status_changed_event(task=task, previous_status=previous_status, changed_by=changed_by)
        )
        from apps.integrations.email.services import queue_task_status_changed_email

        recipients = []
        for user in [task.assigned_to, task.created_by]:
            if user is None:
                continue
            if changed_by and user.id == changed_by.id:
                continue
            if any(existing.id == user.id for existing in recipients):
                continue
            recipients.append(user)

        for recipient in recipients:
            transaction.on_commit(
                lambda recipient=recipient: queue_task_status_changed_email(
                    task=task,
                    previous_status=previous_status,
                    changed_by=changed_by,
                    recipient=recipient,
                )
            )
    return task


def get_overdue_tasks(*, team: Team):
    return (
        Task.objects.filter(team=team, is_archived=False)
        .exclude(status=Task.Status.DONE)
        .filter(due_date__lt=timezone.now())
    )
