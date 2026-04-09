from __future__ import annotations

from datetime import datetime, time, timedelta
from types import SimpleNamespace

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, create_audit_log, log_task_action
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
from apps.tasks.models import (
    AutomationRule,
    GuestTaskAccess,
    Milestone,
    SavedTaskView,
    Task,
    TaskDependency,
    TaskTemplate,
    TimeEntry,
)
from apps.tasks.models import FavoriteTask, RecentTaskVisit, TaskChecklistItem, TaskLabel, TaskWatcher
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


def _resolve_template_dates(*, template: TaskTemplate, planned_for_date=None, due_date=None):
    resolved_planned_for_date = planned_for_date
    resolved_due_date = due_date

    if resolved_planned_for_date is None and template.planned_offset_days is not None:
        resolved_planned_for_date = timezone.localdate() + timedelta(days=template.planned_offset_days)

    if resolved_due_date is None and template.due_offset_days is not None:
        due_day = timezone.localdate() + timedelta(days=template.due_offset_days)
        resolved_due_date = timezone.make_aware(datetime.combine(due_day, time(hour=17, minute=0)))

    return resolved_planned_for_date, resolved_due_date


def validate_task_assignment(*, team: Team, user: User | None) -> User | None:
    if user is None:
        return None
    if team.is_personal:
        raise ValidationError({"assigned_to": ["Personal tasks cannot be assigned to another user."]})
    if not user.is_active:
        raise ValidationError({"assigned_to": ["Selected user is inactive."]})
    membership = Membership.objects.filter(team=team, user=user, status=Membership.Status.ACTIVE).first()
    if not membership:
        raise ValidationError({"assigned_to": ["Selected user is not a member of this team."]})
    return user


def validate_task_labels(*, team: Team, labels) -> list[TaskLabel]:
    if not labels:
        return []
    label_ids = [str(label.id if hasattr(label, "id") else label) for label in labels]
    queryset = list(TaskLabel.objects.filter(team=team, id__in=label_ids))
    if len(queryset) != len(set(label_ids)):
        raise ValidationError({"labels": ["One or more labels do not belong to this team."]})
    return queryset


def _sync_completion_metadata(*, task: Task, previous_status: str, new_status: str, changed_by: User | None) -> None:
    if previous_status == new_status:
        return
    task.last_status_changed_at = timezone.now()
    task.last_status_changed_by = changed_by
    if new_status == Task.Status.DONE:
        task.completed_at = timezone.now()
    elif previous_status == Task.Status.DONE:
        task.completed_at = None


def _dependency_has_cycle(*, from_task: Task, to_task: Task) -> bool:
    if from_task.id == to_task.id:
        return True
    visited = set()
    stack = [to_task.id]
    while stack:
        current_id = stack.pop()
        if current_id in visited:
            continue
        visited.add(current_id)
        if current_id == from_task.id:
            return True
        next_ids = TaskDependency.objects.filter(
            from_task_id=current_id,
            dependency_type=TaskDependency.DependencyType.BLOCKS,
        ).values_list("to_task_id", flat=True)
        stack.extend([task_id for task_id in next_ids if task_id not in visited])
    return False


def create_task_dependency(*, from_task: Task, to_task: Task, dependency_type: str, actor: User | None = None) -> TaskDependency:
    if from_task.team_id != to_task.team_id:
        raise ValidationError({"to_task_id": ["Dependencies must belong to the same team."]})
    if from_task.id == to_task.id:
        raise ValidationError({"to_task_id": ["A task cannot depend on itself."]})
    if dependency_type == TaskDependency.DependencyType.BLOCKS and _dependency_has_cycle(from_task=from_task, to_task=to_task):
        raise ValidationError({"to_task_id": ["This dependency would create a cycle."]})

    dependency, _created = TaskDependency.objects.get_or_create(
        from_task=from_task,
        to_task=to_task,
        dependency_type=dependency_type,
    )
    log_task_action(
        actor=actor,
        action=AuditAction.TASK_UPDATED,
        task=from_task,
        metadata=build_audit_metadata(
            dependency_action="created",
            dependency_type=dependency_type,
            from_task_id=str(from_task.id),
            to_task_id=str(to_task.id),
        ),
    )
    return dependency


def delete_task_dependency(*, dependency: TaskDependency, actor: User | None = None) -> None:
    from_task = dependency.from_task
    dependency_id = str(dependency.id)
    dependency.delete()
    log_task_action(
        actor=actor,
        action=AuditAction.TASK_UPDATED,
        task=from_task,
        metadata=build_audit_metadata(
            dependency_action="deleted",
            dependency_id=dependency_id,
        ),
    )


def create_milestone(*, team: Team, title: str, description: str = "", status: str = Milestone.Status.PLANNED, due_date=None, actor: User | None = None) -> Milestone:
    milestone = Milestone.objects.create(
        team=team,
        title=title.strip(),
        description=(description or "").strip(),
        status=status,
        due_date=due_date,
        created_by=actor,
    )
    create_audit_log(
        actor=actor,
        action=AuditAction.TASK_CREATED,
        target_type="milestone",
        target_id=str(milestone.id),
        target_repr=milestone.title,
        metadata=build_audit_metadata(team_id=str(team.id), status=status),
    )
    return milestone


def update_milestone(*, milestone: Milestone, actor: User | None = None, **kwargs) -> Milestone:
    changed_fields = []
    for field in ("title", "description", "status", "due_date"):
        if field in kwargs:
            setattr(milestone, field, kwargs[field])
            changed_fields.append(field)
    milestone.save(update_fields=[*changed_fields, "updated_at"])
    create_audit_log(
        actor=actor,
        action=AuditAction.TASK_UPDATED,
        target_type="milestone",
        target_id=str(milestone.id),
        target_repr=milestone.title,
        metadata=build_audit_metadata(updated_fields=changed_fields),
    )
    return milestone


def delete_milestone(*, milestone: Milestone, actor: User | None = None) -> None:
    milestone_id = str(milestone.id)
    milestone_title = milestone.title
    milestone.delete()
    create_audit_log(
        actor=actor,
        action=AuditAction.TASK_DELETED,
        target_type="milestone",
        target_id=milestone_id,
        target_repr=milestone_title,
        metadata=build_audit_metadata(),
    )


def create_time_entry(*, task: Task, user: User, start_time, end_time=None, notes: str = "") -> TimeEntry:
    if end_time and end_time < start_time:
        raise ValidationError({"end_time": ["End time must be after start time."]})
    duration_seconds = 0
    if end_time:
        duration_seconds = int((end_time - start_time).total_seconds())
    return TimeEntry.objects.create(
        task=task,
        user=user,
        start_time=start_time,
        end_time=end_time,
        duration_seconds=max(duration_seconds, 0),
        notes=(notes or "").strip(),
    )


def start_time_entry(*, task: Task, user: User, start_time=None) -> TimeEntry:
    if TimeEntry.objects.filter(user=user, end_time__isnull=True).exists():
        raise ValidationError({"time_entry": ["Stop your current timer before starting a new one."]})
    return create_time_entry(task=task, user=user, start_time=start_time or timezone.now())


def stop_time_entry(*, entry: TimeEntry, end_time=None) -> TimeEntry:
    if entry.end_time:
        return entry
    resolved_end = end_time or timezone.now()
    if resolved_end < entry.start_time:
        raise ValidationError({"end_time": ["End time must be after start time."]})
    entry.end_time = resolved_end
    entry.duration_seconds = max(int((resolved_end - entry.start_time).total_seconds()), 0)
    entry.save(update_fields=["end_time", "duration_seconds"])
    return entry


def _condition_matches(*, payload: dict, conditions: dict) -> bool:
    for key, expected in (conditions or {}).items():
        actual = payload.get(key)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def evaluate_automation_rules(*, trigger: str, actor: User | None, team: Team | None = None, payload: dict | None = None) -> int:
    payload = payload or {}
    queryset = AutomationRule.objects.filter(is_active=True, trigger_type=trigger)
    if team is not None:
        queryset = queryset.filter(team=team)
    executed = 0
    for rule in queryset:
        if not _condition_matches(payload=payload, conditions=rule.conditions):
            continue
        _execute_automation_action(rule=rule, actor=actor, payload=payload)
        executed += 1
    return executed


def _execute_automation_action(*, rule: AutomationRule, actor: User | None, payload: dict) -> None:
    action_payload = rule.action_payload or {}
    if rule.action_type == AutomationRule.Action.CREATE_NOTIFICATION:
        from apps.notifications.services import create_notification

        user_id = action_payload.get("user_id") or payload.get("assignee_id")
        if not user_id:
            return
        create_notification(
            user=User.objects.filter(id=user_id).first(),
            notification_type=action_payload.get("notification_type", "admin_message"),
            title=action_payload.get("title", rule.name),
            message=action_payload.get("message", "Automation triggered."),
            actor=actor,
            team=rule.team,
            metadata={"automation_rule_id": str(rule.id)},
        )
        return

    if rule.action_type == AutomationRule.Action.SEND_EMAIL:
        from apps.integrations.email.services import queue_admin_communication_email
        recipient_id = action_payload.get("user_id") or payload.get("assignee_id")
        recipient = User.objects.filter(id=recipient_id).first() if recipient_id else None
        if recipient is None:
            return
        communication = None
        queue_admin_communication_email(
            communication=SimpleNamespace(
                id=str(rule.id),
                title=action_payload.get("title", rule.name),
                message=action_payload.get("message", "Automation triggered."),
                audience_type="automation",
                channel_type="email",
                cta_label=action_payload.get("cta_label", ""),
                cta_link=action_payload.get("cta_link", ""),
            ),
            recipient=recipient,
            actor=actor,
        )
        return

    if rule.action_type == AutomationRule.Action.ASSIGN_USER:
        task_id = payload.get("task_id")
        assignee_id = action_payload.get("assignee_id")
        if not task_id or not assignee_id:
            return
        task = Task.objects.filter(id=task_id).first()
        assignee = User.objects.filter(id=assignee_id).first()
        if task and assignee:
            assign_task(task=task, user=assignee, actor=actor)
        return

    if rule.action_type == AutomationRule.Action.CHANGE_STATUS:
        task_id = payload.get("task_id")
        next_status = action_payload.get("status")
        if not task_id or not next_status:
            return
        task = Task.objects.filter(id=task_id).first()
        if task:
            change_task_status(task=task, new_status=next_status, changed_by=actor)
        return

    if rule.action_type == AutomationRule.Action.ADD_LABEL:
        task_id = payload.get("task_id")
        label_id = action_payload.get("label_id")
        if not task_id or not label_id:
            return
        task = Task.objects.filter(id=task_id).first()
        label = TaskLabel.objects.filter(id=label_id, team=rule.team).first()
        if task and label:
            task.labels.add(label)
        return

    if rule.action_type == AutomationRule.Action.CREATE_FOLLOW_UP_TASK:
        task_id = payload.get("task_id")
        task = Task.objects.filter(id=task_id).first() if task_id else None
        if task:
            create_task(
                team=task.team,
                title=action_payload.get("title", f"Follow-up: {task.title}"),
                description=action_payload.get("description", ""),
                created_by=actor,
                assigned_to=task.assigned_to,
            )
        return

    if rule.action_type == AutomationRule.Action.NOTIFY_ADMIN:
        from apps.notifications.constants import NotificationType
        from apps.notifications.services import create_notification

        admin_memberships = (
            Membership.objects.filter(
                team=rule.team,
                status=Membership.Status.ACTIVE,
                role=Membership.Role.ADMIN,
                user__is_active=True,
            )
            .select_related("user")
        )
        title = action_payload.get("title", rule.name)
        message = action_payload.get("message", "Automation triggered.")
        metadata = {
            "automation_rule_id": str(rule.id),
            "task_id": str(payload.get("task_id") or ""),
        }
        for membership in admin_memberships:
            create_notification(
                user=membership.user,
                notification_type=NotificationType.ADMIN_MESSAGE,
                title=title,
                message=message,
                actor=actor,
                team=rule.team,
                metadata=metadata,
            )
        return


@transaction.atomic
def create_task(
    *,
    team: Team,
    title: str,
    description: str = "",
    status: str = Task.Status.TODO,
    priority: str = Task.Priority.MEDIUM,
    estimated_minutes: int | None = None,
    planned_for_date=None,
    start_at=None,
    blocked_reason: str = "",
    due_date=None,
    recurrence_pattern: str = Task.Recurrence.NONE,
    recurrence_interval: int = 1,
    created_by: User | None,
    assigned_to: User | None = None,
    source_template: TaskTemplate | None = None,
    labels: list[TaskLabel] | None = None,
    position: int | None = None,
    milestone: Milestone | None = None,
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
        estimated_minutes=estimated_minutes,
        planned_for_date=planned_for_date,
        start_at=start_at,
        blocked_reason=blocked_reason,
        due_date=due_date,
        recurrence_pattern=recurrence_pattern,
        recurrence_interval=recurrence_interval,
        assigned_to=assigned_user,
        created_by=created_by,
        source_template=source_template,
        milestone=milestone,
        position=position if position is not None else _get_task_position(team=team, status=status),
    )
    if labels:
        task.labels.set(labels)
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
            estimated_minutes=task.estimated_minutes,
            planned_for_date=task.planned_for_date,
            start_at=task.start_at,
            assigned_to_id=task.assigned_to_id,
            due_date=task.due_date,
            recurrence_pattern=task.recurrence_pattern,
            label_ids=[label.id for label in task.labels.all()],
        ),
    )
    transaction.on_commit(lambda: send_task_created_event(task=task))
    transaction.on_commit(
        lambda: evaluate_automation_rules(
            trigger=AutomationRule.Trigger.TASK_CREATED,
            actor=created_by,
            team=team,
            payload={"task_id": str(task.id), "status": task.status, "priority": task.priority},
        )
    )

    if assigned_user and created_by and assigned_user.id != created_by.id:
        from apps.notifications.services import notify_task_assignment

        transaction.on_commit(lambda: notify_task_assignment(task=task, actor=created_by))
        transaction.on_commit(lambda: send_task_assignment_event(task=task, actor=created_by))
    return task


@transaction.atomic
def update_task(
    *,
    task: Task,
    actor,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    estimated_minutes=UNSET,
    planned_for_date=UNSET,
    start_at=UNSET,
    blocked_reason=UNSET,
    due_date=UNSET,
    recurrence_pattern: str | None = None,
    recurrence_interval: int | None = None,
    labels=UNSET,
    position: int | None = None,
    milestone=UNSET,
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
    if estimated_minutes is not UNSET:
        changed_fields["estimated_minutes"] = {"old": task.estimated_minutes, "new": estimated_minutes}
        task.estimated_minutes = estimated_minutes
    if planned_for_date is not UNSET:
        changed_fields["planned_for_date"] = {"old": task.planned_for_date, "new": planned_for_date}
        task.planned_for_date = planned_for_date
    if start_at is not UNSET:
        changed_fields["start_at"] = {"old": task.start_at, "new": start_at}
        task.start_at = start_at
    if blocked_reason is not UNSET:
        normalized_blocked_reason = (blocked_reason or "").strip()
        changed_fields["blocked_reason"] = {"old": task.blocked_reason, "new": normalized_blocked_reason}
        task.blocked_reason = normalized_blocked_reason
    if due_date is not UNSET:
        changed_fields["due_date"] = {"old": task.due_date, "new": due_date}
        task.due_date = due_date
    if recurrence_pattern is not None:
        changed_fields["recurrence_pattern"] = {"old": task.recurrence_pattern, "new": recurrence_pattern}
        task.recurrence_pattern = recurrence_pattern
    if recurrence_interval is not None:
        changed_fields["recurrence_interval"] = {"old": task.recurrence_interval, "new": recurrence_interval}
        task.recurrence_interval = recurrence_interval
    if labels is not UNSET:
        previous_label_ids = list(task.labels.values_list("id", flat=True))
        next_label_ids = [label.id for label in labels]
        changed_fields["labels"] = {"old": previous_label_ids, "new": next_label_ids}
    if position is not None:
        changed_fields["position"] = {"old": task.position, "new": position}
        task.position = position
    if milestone is not UNSET:
        changed_fields["milestone"] = {"old": str(task.milestone_id) if task.milestone_id else None, "new": str(milestone.id) if milestone else None}
        task.milestone = milestone
    task.save()
    if labels is not UNSET:
        task.labels.set(labels)
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

        transaction.on_commit(lambda: notify_task_assignment(task=task, actor=actor))
        transaction.on_commit(lambda: send_task_assignment_event(task=task, actor=actor))
        transaction.on_commit(
            lambda: evaluate_automation_rules(
                trigger=AutomationRule.Trigger.TASK_ASSIGNED,
                actor=actor,
                team=task.team,
                payload={"task_id": str(task.id), "assignee_id": str(task.assigned_to_id)},
            )
        )
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
        if new_status == Task.Status.DONE:
            _spawn_next_recurring_task(task=task, changed_by=changed_by)
        transaction.on_commit(
            lambda: send_task_status_changed_event(task=task, previous_status=previous_status, changed_by=changed_by)
        )
        transaction.on_commit(
            lambda: evaluate_automation_rules(
                trigger=AutomationRule.Trigger.TASK_STATUS_CHANGED,
                actor=changed_by,
                team=task.team,
                payload={"task_id": str(task.id), "status": new_status},
            )
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


@transaction.atomic
def create_task_template(
    *,
    team: Team,
    name: str,
    title: str,
    description: str = "",
    priority: str = Task.Priority.MEDIUM,
    estimated_minutes: int | None = None,
    planned_offset_days: int | None = None,
    due_offset_days: int | None = None,
    blocked_reason: str = "",
    recurrence_pattern: str = Task.Recurrence.NONE,
    recurrence_interval: int = 1,
    created_by: User,
    assigned_to: User | None = None,
) -> TaskTemplate:
    assigned_user = validate_task_assignment(team=team, user=assigned_to)
    return TaskTemplate.objects.create(
        team=team,
        name=name.strip(),
        title=title.strip(),
        description=description,
        priority=priority,
        estimated_minutes=estimated_minutes,
        planned_offset_days=planned_offset_days,
        due_offset_days=due_offset_days,
        blocked_reason=blocked_reason.strip(),
        recurrence_pattern=recurrence_pattern,
        recurrence_interval=recurrence_interval,
        assigned_to=assigned_user,
        created_by=created_by,
    )


@transaction.atomic
def create_task_label(*, team: Team, name: str, color: str = "#10b981", created_by: User | None = None) -> TaskLabel:
    label = TaskLabel.objects.create(
        team=team,
        name=name.strip(),
        color=(color or "#10b981").strip()[:16],
        created_by=created_by,
    )
    create_audit_log(
        actor=created_by,
        action=AuditAction.TASK_LABEL_CREATED,
        team=team,
        target=label,
        metadata=build_audit_metadata(label_id=label.id, label_name=label.name, label_color=label.color),
    )
    return label


def _get_checklist_position(*, task: Task) -> int:
    return (TaskChecklistItem.objects.filter(task=task).aggregate(max_position=Max("position"))["max_position"] or 0) + 1


@transaction.atomic
def create_checklist_item(*, task: Task, title: str, created_by: User | None = None) -> TaskChecklistItem:
    item = TaskChecklistItem.objects.create(
        task=task,
        title=title.strip(),
        position=_get_checklist_position(task=task),
        created_by=created_by,
    )
    log_task_action(
        actor=created_by,
        action=AuditAction.TASK_CHECKLIST_CREATED,
        task=task,
        metadata=build_audit_metadata(task_id=task.id, checklist_item_id=item.id, checklist_title=item.title),
    )
    return item


@transaction.atomic
def update_checklist_item(*, item: TaskChecklistItem, actor: User | None = None, title=UNSET, is_completed=UNSET, position=UNSET) -> TaskChecklistItem:
    changes = {}
    if title is not UNSET:
        normalized_title = str(title).strip()
        changes["title"] = {"old": item.title, "new": normalized_title}
        item.title = normalized_title
    if is_completed is not UNSET:
        normalized_completed = bool(is_completed)
        changes["is_completed"] = {"old": item.is_completed, "new": normalized_completed}
        item.is_completed = normalized_completed
        item.completed_at = timezone.now() if normalized_completed else None
        item.completed_by = actor if normalized_completed else None
    if position is not UNSET:
        changes["position"] = {"old": item.position, "new": position}
        item.position = position
    item.save()
    if changes:
        log_task_action(
            actor=actor,
            action=AuditAction.TASK_CHECKLIST_UPDATED,
            task=item.task,
            metadata=build_audit_metadata(task_id=item.task_id, checklist_item_id=item.id, changes=changes),
        )
    return item


@transaction.atomic
def delete_checklist_item(*, item: TaskChecklistItem, actor: User | None = None) -> None:
    task = item.task
    metadata = build_audit_metadata(task_id=task.id, checklist_item_id=item.id, checklist_title=item.title)
    item.delete()
    log_task_action(actor=actor, action=AuditAction.TASK_CHECKLIST_DELETED, task=task, metadata=metadata)


@transaction.atomic
def add_task_watcher(*, task: Task, user: User) -> tuple[TaskWatcher, bool]:
    watcher, created = TaskWatcher.objects.get_or_create(task=task, user=user)
    if created:
        log_task_action(
            actor=user,
            action=AuditAction.TASK_WATCHER_ADDED,
            task=task,
            metadata=build_audit_metadata(task_id=task.id, watcher_id=user.id),
        )
    return watcher, created


@transaction.atomic
def remove_task_watcher(*, task: Task, user: User) -> bool:
    deleted, _details = TaskWatcher.objects.filter(task=task, user=user).delete()
    if deleted:
        log_task_action(
            actor=user,
            action=AuditAction.TASK_WATCHER_REMOVED,
            task=task,
            metadata=build_audit_metadata(task_id=task.id, watcher_id=user.id),
        )
    return bool(deleted)


@transaction.atomic
def toggle_favorite_task(*, task: Task, user: User) -> bool:
    favorite, created = FavoriteTask.objects.get_or_create(task=task, user=user)
    if created:
        log_task_action(
            actor=user,
            action=AuditAction.TASK_FAVORITED,
            task=task,
            metadata=build_audit_metadata(task_id=task.id),
        )
        return True

    favorite.delete()
    log_task_action(
        actor=user,
        action=AuditAction.TASK_UNFAVORITED,
        task=task,
        metadata=build_audit_metadata(task_id=task.id),
    )
    return False


def touch_recent_task(*, task: Task, user: User) -> None:
    RecentTaskVisit.objects.update_or_create(
        task=task,
        user=user,
        defaults={"last_accessed_at": timezone.now()},
    )


@transaction.atomic
def bulk_update_tasks(*, tasks, actor: User, action: str, status: str | None = None, assigned_to: User | None = None) -> list[Task]:
    updated_tasks: list[Task] = []
    for task in tasks:
        if action == "status" and status:
            updated_tasks.append(change_task_status(task=task, new_status=status, changed_by=actor))
        elif action == "assign":
            updated_tasks.append(assign_task(task=task, user=assigned_to, actor=actor))
        elif action == "archive":
            updated_tasks.append(archive_task(task=task, actor=actor))
    if updated_tasks:
        sample_task = updated_tasks[0]
        log_task_action(
            actor=actor,
            action=AuditAction.TASK_BULK_UPDATED,
            task=sample_task,
            metadata=build_audit_metadata(
                task_id=sample_task.id,
                affected_task_ids=[task.id for task in updated_tasks],
                bulk_action=action,
                status=status,
                assigned_to_id=getattr(assigned_to, "id", None),
            ),
        )
    return updated_tasks


@transaction.atomic
def create_task_from_template(
    *,
    template: TaskTemplate,
    actor: User,
    planned_for_date=None,
    due_date=None,
    assigned_to: User | None = None,
) -> Task:
    assigned_user = validate_task_assignment(team=template.team, user=assigned_to or template.assigned_to)
    resolved_planned_for_date, resolved_due_date = _resolve_template_dates(
        template=template,
        planned_for_date=planned_for_date,
        due_date=due_date,
    )
    return create_task(
        team=template.team,
        title=template.title,
        description=template.description,
        priority=template.priority,
        estimated_minutes=template.estimated_minutes,
        planned_for_date=resolved_planned_for_date,
        blocked_reason=template.blocked_reason,
        due_date=resolved_due_date,
        recurrence_pattern=template.recurrence_pattern,
        recurrence_interval=template.recurrence_interval,
        created_by=actor,
        assigned_to=assigned_user,
        source_template=template,
    )


@transaction.atomic
def create_saved_task_view(
    *,
    user,
    name: str,
    layout: str,
    filters: dict | None = None,
    team: Team | None = None,
    is_default: bool = False,
    is_shared: bool = False,
    is_pinned: bool = False,
):
    if is_default:
        SavedTaskView.objects.filter(user=user, team=team, layout=layout).update(is_default=False)
    saved_view, _created = SavedTaskView.objects.update_or_create(
        user=user,
        team=team,
        name=name.strip(),
        defaults={
            "layout": layout,
            "filters": filters or {},
            "is_default": is_default,
            "is_shared": is_shared,
            "is_pinned": is_pinned,
        },
    )
    return saved_view


@transaction.atomic
def update_saved_task_view(*, saved_view: SavedTaskView, data: dict) -> SavedTaskView:
    if data.get("is_default"):
        SavedTaskView.objects.filter(
            user=saved_view.user,
            team=saved_view.team,
            layout=data.get("layout") or saved_view.layout,
        ).exclude(pk=saved_view.pk).update(is_default=False)

    for field in ("name", "layout", "filters", "is_default", "is_shared", "is_pinned"):
        if field in data:
            setattr(saved_view, field, data[field])
    saved_view.save(update_fields=["name", "layout", "filters", "is_default", "is_shared", "is_pinned", "updated_at"])
    return saved_view


def delete_saved_task_view(*, saved_view: SavedTaskView) -> None:
    saved_view.delete()


def _spawn_next_recurring_task(*, task: Task, changed_by: User | None = None) -> Task | None:
    if task.recurrence_pattern == Task.Recurrence.NONE or not task.is_recurring_active:
        return None

    next_planned_for_date, next_due_date = task.build_next_recurrence_dates()
    if next_planned_for_date is None and next_due_date is None:
        return None

    next_task = create_task(
        team=task.team,
        title=task.title,
        description=task.description,
        status=Task.Status.TODO,
        priority=task.priority,
        estimated_minutes=task.estimated_minutes,
        planned_for_date=next_planned_for_date,
        blocked_reason=task.blocked_reason,
        due_date=next_due_date,
        recurrence_pattern=task.recurrence_pattern,
        recurrence_interval=task.recurrence_interval,
        created_by=changed_by or task.created_by or task.assigned_to,
        assigned_to=task.assigned_to,
        source_template=task.source_template,
    )
    task.is_recurring_active = False
    task.save(update_fields=["is_recurring_active", "updated_at"])
    return next_task


def get_overdue_tasks(*, team: Team):
    return (
        Task.objects.filter(team=team, is_archived=False)
        .exclude(status=Task.Status.DONE)
        .filter(due_date__lt=timezone.now())
    )
