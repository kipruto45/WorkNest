from __future__ import annotations

from collections import Counter
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone

from apps.audit_logs.constants import AuditAction
from apps.audit_logs.models import AuditLog
from apps.common.health import get_cache_health, get_database_health
from apps.common.utils import get_api_version, get_runtime_environment
from apps.dashboards.constants import (
    PERCENTAGE_PRECISION,
    TASK_PRIORITY_ORDER,
    TASK_STATUS_ORDER,
)
from apps.dashboards.queries import aggregate_task_counts
from apps.dashboards.selectors import (
    get_team_deadline_feed,
    get_team_member_activity,
    get_team_priority_counts,
    get_team_status_counts,
    get_team_tasks,
    get_team_workload_distribution,
    get_user_deadline_feed,
    get_user_priority_counts,
    get_user_status_counts,
    get_user_assigned_tasks,
    get_user_completed_tasks_this_week,
)
from apps.memberships.models import TeamInvitation
from apps.notifications.models import Notification
from apps.tasks.models import Task
from apps.teams.models import Team

User = get_user_model()


def _calculate_percentage(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((part / total) * 100, PERCENTAGE_PRECISION)


def _build_distribution(*, raw_counts: list[dict], order: list[str], key_name: str, enum_class) -> list[dict]:
    counts_by_key = {item[key_name]: item["count"] for item in raw_counts}
    total = sum(counts_by_key.values())
    return [
        {
            key_name: value,
            "label": enum_class(value).label,
            "count": counts_by_key.get(value, 0),
            "percentage": _calculate_percentage(counts_by_key.get(value, 0), total),
        }
        for value in order
    ]


def _serialize_member_activity(memberships) -> list[dict]:
    member_activity = []
    for membership in memberships:
        last_activity_at = membership.last_task_activity_at
        if membership.last_comment_activity_at and (
            last_activity_at is None or membership.last_comment_activity_at > last_activity_at
        ):
            last_activity_at = membership.last_comment_activity_at

        member_activity.append(
            {
                "user_id": membership.user_id,
                "name": membership.user.name,
                "email": membership.user.email,
                "avatar": membership.user.avatar,
                "role": membership.role,
                "assigned_tasks": membership.assigned_count,
                "completed_tasks": membership.completed_count,
                "open_tasks": membership.open_count,
                "overdue_tasks": membership.overdue_count,
                "comment_count": membership.comment_count,
                "completion_rate": _calculate_percentage(membership.completed_count, membership.assigned_count),
                "last_activity_at": last_activity_at,
            }
        )
    return member_activity


def build_status_distribution(*, user=None, team=None) -> list[dict]:
    if team is not None:
        raw_counts = get_team_status_counts(team)
    else:
        raw_counts = get_user_status_counts(user)
    return _build_distribution(
        raw_counts=raw_counts,
        order=TASK_STATUS_ORDER,
        key_name="status",
        enum_class=Task.Status,
    )


def build_priority_distribution(*, user=None, team=None) -> list[dict]:
    if team is not None:
        raw_counts = get_team_priority_counts(team)
    else:
        raw_counts = get_user_priority_counts(user)
    return _build_distribution(
        raw_counts=raw_counts,
        order=TASK_PRIORITY_ORDER,
        key_name="priority",
        enum_class=Task.Priority,
    )


def build_personal_dashboard_summary(*, user, reference_time=None) -> dict:
    now = reference_time or timezone.now()
    assigned_tasks = get_user_assigned_tasks(user)
    counts = aggregate_task_counts(assigned_tasks, reference_time=now)
    completed_this_week = get_user_completed_tasks_this_week(user, reference_time=now).count()

    return {
        "summary": {
            "assigned_tasks": counts["total_tasks"],
            "overdue_tasks": counts["overdue_tasks"],
            "completed_this_week": completed_this_week,
            "due_today": counts["due_today_tasks"],
            "due_soon": counts["due_soon_tasks"],
            "completion_rate": _calculate_percentage(counts["completed_tasks"], counts["total_tasks"]),
        },
        "status_distribution": build_status_distribution(user=user),
        "priority_distribution": build_priority_distribution(user=user),
    }


def build_team_dashboard_summary(*, team, reference_time=None) -> dict:
    now = reference_time or timezone.now()
    team_tasks = get_team_tasks(team)
    counts = aggregate_task_counts(team_tasks, reference_time=now)
    member_activity = build_member_activity_metrics(team=team, reference_time=now)

    return {
        "summary": {
            "total_tasks": counts["total_tasks"],
            "completed_tasks": counts["completed_tasks"],
            "pending_tasks": counts["pending_tasks"],
            "overdue_tasks": counts["overdue_tasks"],
            "in_progress_tasks": counts["in_progress_tasks"],
            "due_today": counts["due_today_tasks"],
            "due_soon": counts["due_soon_tasks"],
            "unassigned_tasks": counts["unassigned_tasks"],
            "completion_rate": _calculate_percentage(counts["completed_tasks"], counts["total_tasks"]),
            "overdue_rate": _calculate_percentage(counts["overdue_tasks"], counts["total_tasks"]),
            "member_count": len(member_activity),
        },
        "status_distribution": build_status_distribution(team=team),
        "priority_distribution": build_priority_distribution(team=team),
        "member_activity": member_activity,
    }


def build_team_progress_metrics(*, team, reference_time=None) -> dict:
    now = reference_time or timezone.now()
    team_tasks = get_team_tasks(team)
    counts = aggregate_task_counts(team_tasks, reference_time=now)
    member_activity = build_member_activity_metrics(team=team, reference_time=now)

    return {
        "progress": {
            "completed_tasks": counts["completed_tasks"],
            "pending_tasks": counts["pending_tasks"],
            "overdue_tasks": counts["overdue_tasks"],
            "active_tasks": counts["pending_tasks"],
            "total_tasks": counts["total_tasks"],
            "completion_rate": _calculate_percentage(counts["completed_tasks"], counts["total_tasks"]),
            "overdue_rate": _calculate_percentage(counts["overdue_tasks"], counts["total_tasks"]),
        },
        "progress_bar": {
            "completed": counts["completed_tasks"],
            "total": counts["total_tasks"],
            "percentage": _calculate_percentage(counts["completed_tasks"], counts["total_tasks"]),
        },
        "status_breakdown": build_status_distribution(team=team),
        "priority_breakdown": build_priority_distribution(team=team),
        "member_progress": member_activity,
    }


def build_member_activity_metrics(*, team, reference_time=None) -> list[dict]:
    memberships = get_team_member_activity(team, reference_time=reference_time)
    return _serialize_member_activity(memberships)


def build_workload_distribution(*, team, reference_time=None) -> list[dict]:
    memberships = get_team_workload_distribution(team, reference_time=reference_time)
    return [
        {
            "user_id": membership.user_id,
            "name": membership.user.name,
            "email": membership.user.email,
            "avatar": membership.user.avatar,
            "assigned_tasks": membership.assigned_count,
            "completed_tasks": membership.completed_count,
            "open_tasks": membership.open_count,
            "overdue_tasks": membership.overdue_count,
            "completion_rate": _calculate_percentage(membership.completed_count, membership.assigned_count),
        }
        for membership in memberships
    ]


def build_deadline_calendar_feed(
    *,
    user=None,
    team=None,
    team_id=None,
    start=None,
    end=None,
    assignee_id=None,
    status=None,
    priority=None,
):
    if team is not None:
        return get_team_deadline_feed(
            team,
            start=start,
            end=end,
            assignee_id=assignee_id,
            status=status,
            priority=priority,
        )
    return get_user_deadline_feed(
        user,
        start=start,
        end=end,
        team_id=team_id,
        status=status,
        priority=priority,
    )


def build_admin_dashboard_snapshot(*, reference_time=None) -> dict:
    now = reference_time or timezone.now()
    seven_days_ago = now - timedelta(days=6)
    users_queryset = User.objects.all()
    teams_queryset = Team.objects.filter(is_archived=False)
    tasks_queryset = Task.objects.filter(is_archived=False)
    audit_queryset = AuditLog.objects.select_related("actor", "team").all()
    notifications_queryset = Notification.objects.all()
    pending_invites_queryset = TeamInvitation.objects.filter(
        status=TeamInvitation.Status.PENDING,
        expires_at__gt=now,
    )

    recent_audit_logs = audit_queryset.filter(created_at__gte=seven_days_ago)
    recent_user_actions = recent_audit_logs.exclude(actor_id__isnull=True)

    team_map: dict[str, dict] = {
        str(team.id): {
            "id": str(team.id),
            "name": team.name,
            "task_count": 0,
            "overdue_count": 0,
            "activity_count": 0,
            "updated_at": team.updated_at,
        }
        for team in teams_queryset
    }

    for task in tasks_queryset:
        team_entry = team_map.get(str(task.team_id))
        if not team_entry:
            continue
        team_entry["task_count"] += 1
        if task.due_date and task.due_date < now and task.status != Task.Status.DONE:
            team_entry["overdue_count"] += 1

    for log in recent_audit_logs:
        if not log.team_id:
            continue
        team_entry = team_map.get(str(log.team_id))
        if not team_entry:
            continue
        team_entry["activity_count"] += 1

    team_values = list(team_map.values())
    login_failures_today = audit_queryset.filter(
        action=AuditAction.USER_LOGIN_FAILED,
        created_at__date=now.date(),
    ).count()

    ops_services = _build_ops_services()
    attention_queue = _build_admin_attention_queue(
        ops_services=ops_services,
        team_values=team_values,
        pending_invites=pending_invites_queryset.count(),
        login_failures_today=login_failures_today,
    )

    return {
        "overview": {
            "total_users": users_queryset.count(),
            "total_teams": teams_queryset.count(),
            "total_tasks": tasks_queryset.count(),
            "active_users": _count_active_users(now=now),
            "pending_invites": pending_invites_queryset.count(),
            "system_activity_today": audit_queryset.filter(created_at__date=now.date()).count(),
            "environment": get_runtime_environment(),
            "version": get_api_version(),
            "health_status": "ok" if all(service["value"] == "ok" or service["value"] == "configured" for service in ops_services) else "degraded",
        },
        "growth": {
            "user_growth": _build_growth_series(users_queryset, field_name="created_at", now=now),
            "team_growth": _build_growth_series(teams_queryset, field_name="created_at", now=now),
            "task_creation": _build_growth_series(tasks_queryset, field_name="created_at", now=now),
            "platform_activity": _build_growth_series(audit_queryset, field_name="created_at", now=now),
        },
        "user_activity": {
            "recently_active_users": _build_recently_active_users(recent_user_actions),
            "new_registrations": _build_new_registrations(users_queryset),
        },
        "team_health": {
            "most_active_teams": sorted(team_values, key=lambda item: (-item["activity_count"], -item["task_count"]))[:5],
            "inactive_teams": sorted(team_values, key=lambda item: (item["activity_count"], item["updated_at"] or now))[:4],
            "overdue_heavy_teams": sorted(
                [item for item in team_values if item["overdue_count"] > 0],
                key=lambda item: (-item["overdue_count"], -item["task_count"]),
            )[:4],
        },
        "notifications": {
            "total_notifications": notifications_queryset.count(),
            "unread_notifications": notifications_queryset.filter(is_read=False).count(),
            "distribution": _build_notification_distribution(notifications_queryset),
        },
        "system_events": _build_system_events(audit_queryset[:8]),
        "ops": {
            "services": ops_services,
            "debug": False,
            "docs_enabled": True,
            "environment": get_runtime_environment(),
            "version": get_api_version(),
        },
        "insights": {
            "attention_queue": attention_queue,
            "admin_insights": [
                {
                    "label": "Pending invitations",
                    "value": pending_invites_queryset.count(),
                    "note": (
                        f"{pending_invites_queryset.count()} invites still awaiting response."
                        if pending_invites_queryset.exists()
                        else "No pending invitations."
                    ),
                },
                {
                    "label": "Teams needing review",
                    "value": len([item for item in team_values if item["overdue_count"] > 0]),
                    "note": (
                        f"{max(team_values, key=lambda item: item['overdue_count'])['name']} has the highest overdue concentration."
                        if any(item["overdue_count"] > 0 for item in team_values)
                        else "No teams show meaningful overdue concentration."
                    ),
                },
                {
                    "label": "Accounts needing review",
                    "value": login_failures_today,
                    "note": (
                        f"{login_failures_today} failed login events were recorded today."
                        if login_failures_today
                        else "No unusual authentication noise detected today."
                    ),
                },
            ],
        },
    }


def _count_active_users(*, now) -> int:
    seven_days_ago = now - timedelta(days=7)
    return User.objects.filter(Q(last_login__gte=seven_days_ago) | Q(audit_logs__created_at__gte=seven_days_ago)).distinct().count()


def _build_growth_series(queryset, *, field_name: str, now, days: int = 7) -> list[dict]:
    start_date = (now - timedelta(days=days - 1)).date()
    counter = Counter(getattr(item, field_name).date() for item in queryset if getattr(item, field_name, None))

    points = []
    for offset in range(days):
        point_date = start_date + timedelta(days=offset)
        points.append(
            {
                "label": point_date.strftime("%a"),
                "date": point_date,
                "count": counter.get(point_date, 0),
            }
        )
    return points


def _build_recently_active_users(audit_queryset) -> list[dict]:
    activity_map: dict[str, dict] = {}

    for log in audit_queryset.order_by("-created_at"):
        if not log.actor_id:
            continue
        key = str(log.actor_id)
        if key not in activity_map:
            activity_map[key] = {
                "id": str(log.actor_id),
                "name": log.actor.name if log.actor else "",
                "email": log.actor.email if log.actor else "",
                "actions": 0,
                "last_seen": log.created_at,
            }
        activity_map[key]["actions"] += 1

    return sorted(
        activity_map.values(),
        key=lambda item: (-item["actions"], -item["last_seen"].timestamp()),
    )[:6]


def _build_new_registrations(users_queryset) -> list[dict]:
    users = users_queryset.order_by("-created_at")[:5]
    return [
        {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "created_at": user.created_at,
            "auth_provider": user.auth_provider,
        }
        for user in users
    ]


def _build_notification_distribution(notifications_queryset) -> list[dict]:
    return [
        {"type": row["type"], "count": row["count"]}
        for row in notifications_queryset.values("type").annotate(count=Count("id")).order_by("-count", "type")[:6]
    ]


def _build_system_events(audit_logs) -> list[dict]:
    return [
        {
            "id": str(log.id),
            "action": log.action,
            "title": log.target_repr or log.get_action_display(),
            "description": _describe_audit_event(log),
            "actor_name": log.actor.name if log.actor else "",
            "team_name": log.team.name if log.team else "",
            "created_at": log.created_at,
        }
        for log in audit_logs
    ]


def _describe_audit_event(log: AuditLog) -> str:
    actor_name = log.actor.name if log.actor else "System"
    target = log.target_repr or (log.target_type or "record")
    return f"{actor_name} triggered {log.get_action_display().lower()} for {target}."


def _build_ops_services() -> list[dict]:
    database_status = get_database_health()
    redis_status = get_cache_health()
    services = [
        {"label": "Database", "value": database_status},
        {"label": "Redis", "value": redis_status},
        {"label": "Realtime", "value": "configured"},
        {"label": "Workers", "value": "configured"},
    ]
    return [{**service, "tone": _status_tone(service["value"])} for service in services]


def _build_admin_attention_queue(*, ops_services, team_values, pending_invites: int, login_failures_today: int) -> list[dict]:
    items = []
    degraded_services = [service for service in ops_services if service["value"] not in {"ok", "configured"}]
    overdue_heavy = sorted([team for team in team_values if team["overdue_count"] > 0], key=lambda item: -item["overdue_count"])

    if degraded_services:
        items.append(
            {
                "severity": "critical",
                "title": "Service degradation detected",
                "description": f"{', '.join(service['label'] for service in degraded_services)} require review based on the latest health signals.",
                "action_label": "Inspect ops",
                "href": "/admin/settings",
            }
        )

    if overdue_heavy and overdue_heavy[0]["overdue_count"] >= 3:
        items.append(
            {
                "severity": "warning",
                "title": "Overdue concentration rising",
                "description": f"{overdue_heavy[0]['name']} is carrying {overdue_heavy[0]['overdue_count']} overdue tasks and should be reviewed.",
                "action_label": "Review teams",
                "href": "/admin/teams",
            }
        )

    if pending_invites >= 5:
        items.append(
            {
                "severity": "warning",
                "title": "Invitation backlog building up",
                "description": f"{pending_invites} pending invites are still open across active teams.",
                "action_label": "Check teams",
                "href": "/admin/teams",
            }
        )

    if login_failures_today >= 3:
        items.append(
            {
                "severity": "warning",
                "title": "Authentication failures need review",
                "description": f"{login_failures_today} failed login events were logged today.",
                "action_label": "Open audit logs",
                "href": "/admin/audit-logs",
            }
        )

    if not items:
        items.append(
            {
                "severity": "healthy",
                "title": "No immediate anomalies detected",
                "description": "Current platform signals look stable across usage, invites, and operational health.",
                "action_label": "View overview",
                "href": "/admin",
            }
        )

    return items


def _status_tone(value: str) -> str:
    if value == "ok":
        return "healthy"
    if value == "configured":
        return "neutral"
    return "warning"
