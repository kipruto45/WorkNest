from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone as dt_timezone
from typing import Iterable
from urllib.parse import urlencode

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.integrations.constants import OAUTH_PROVIDER_GOOGLE
from apps.integrations.models import CalendarConnection, CalendarEventBinding, CalendarImportBatch
from apps.memberships.models import Membership
from apps.tasks.models import Task
from apps.tasks.services import create_task
from apps.teams.permissions import require_team_member
from apps.teams.selectors import get_team_by_id_for_user

GOOGLE_OAUTH_STATE_SALT = "worknest.calendar.google.state"


@dataclass(frozen=True)
class CalendarWorkspaceContext:
    scope: str
    team: object
    membership: Membership | None = None

    @property
    def role(self) -> str:
        if self.scope == CalendarConnection.Scope.PERSONAL:
            return Membership.Role.ADMIN
        return self.membership.role if self.membership else ""

    @property
    def is_member(self) -> bool:
        return self.role == Membership.Role.MEMBER

    @property
    def can_manage_team_calendar(self) -> bool:
        if self.scope != CalendarConnection.Scope.TEAM:
            return True
        return self.role in {Membership.Role.ADMIN, Membership.Role.MANAGER}


def _safe_return_path(value: str | None) -> str:
    candidate = str(value or "").strip()
    if not candidate.startswith("/"):
        return ""
    if candidate.startswith("//"):
        return ""
    return candidate


def _google_timeout_seconds() -> int:
    try:
        return max(5, int(getattr(settings, "GOOGLE_OAUTH_REQUEST_TIMEOUT_SECONDS", 10)))
    except (TypeError, ValueError):
        return 10


def get_personal_workspace(*, user):
    membership = (
        Membership.objects.select_related("team")
        .filter(
            user=user,
            status=Membership.Status.ACTIVE,
            team__is_personal=True,
            team__is_archived=False,
        )
        .first()
    )
    if not membership:
        raise ValidationError({"workspace": "Personal workspace is not available for this account."})
    return membership.team


def resolve_workspace_context(*, user, scope: str, team_id=None) -> CalendarWorkspaceContext:
    if scope == CalendarConnection.Scope.PERSONAL:
        team = get_personal_workspace(user=user)
        return CalendarWorkspaceContext(scope=scope, team=team, membership=None)

    team = get_team_by_id_for_user(team_id=team_id, user=user)
    if not team:
        raise ValidationError({"team_id": "Team not found or unavailable."})
    membership = require_team_member(team=team, user=user)
    return CalendarWorkspaceContext(scope=scope, team=team, membership=membership)


def ensure_team_manage_permission(*, context: CalendarWorkspaceContext, action_label: str) -> None:
    if context.scope == CalendarConnection.Scope.TEAM and not context.can_manage_team_calendar:
        raise PermissionDenied(f"Only admins or managers can {action_label} for team calendar integrations.")


def build_task_queryset_for_context(*, user, context: CalendarWorkspaceContext, filters: dict | None = None):
    filters = filters or {}
    queryset = Task.objects.select_related("team", "assigned_to", "created_by").filter(
        team=context.team,
        is_archived=False,
    )

    if context.scope == CalendarConnection.Scope.TEAM and context.is_member:
        queryset = queryset.filter(assigned_to=user)

    task_ids = filters.get("task_ids") or []
    if task_ids:
        queryset = queryset.filter(id__in=task_ids)

    if not filters.get("include_completed", True):
        queryset = queryset.exclude(status=Task.Status.DONE)

    statuses = filters.get("status") or []
    if statuses:
        queryset = queryset.filter(status__in=statuses)

    priorities = filters.get("priority") or []
    if priorities:
        queryset = queryset.filter(priority__in=priorities)

    assigned_to = filters.get("assigned_to")
    if assigned_to:
        queryset = queryset.filter(assigned_to_id=assigned_to)

    if filters.get("include_my_tasks"):
        queryset = queryset.filter(assigned_to=user)

    due_from = filters.get("due_from")
    if due_from:
        queryset = queryset.filter(due_date__gte=due_from)

    due_to = filters.get("due_to")
    if due_to:
        queryset = queryset.filter(due_date__lte=due_to)

    start_from = filters.get("start_from")
    if start_from:
        queryset = queryset.filter(start_at__gte=start_from)

    start_to = filters.get("start_to")
    if start_to:
        queryset = queryset.filter(start_at__lte=start_to)

    search = str(filters.get("search") or "").strip()
    if search:
        queryset = queryset.filter(title__icontains=search)

    return queryset.order_by("due_date", "start_at", "created_at")


def _ics_escape(value: str) -> str:
    escaped = (value or "").replace("\\", "\\\\")
    escaped = escaped.replace(";", "\\;").replace(",", "\\,").replace("\r\n", "\n").replace("\n", "\\n")
    return escaped


def _to_ics_datetime(value: datetime | None) -> str:
    if not value:
        return ""
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    utc_value = value.astimezone(dt_timezone.utc)
    return utc_value.strftime("%Y%m%dT%H%M%SZ")


def build_ics_content(*, tasks: Iterable[Task], calendar_name: str = "WorkNest Tasks") -> str:
    now_stamp = datetime.now(tz=dt_timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//WorkNest//Task Calendar//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_ics_escape(calendar_name)}",
    ]

    for task in tasks:
        start_at = task.start_at or task.due_date or timezone.now()
        if timezone.is_naive(start_at):
            start_at = timezone.make_aware(start_at, timezone.get_current_timezone())
        due_date = task.due_date
        if due_date and timezone.is_naive(due_date):
            due_date = timezone.make_aware(due_date, timezone.get_current_timezone())
        end_at = due_date or (start_at + timedelta(hours=1))
        description_parts = [task.description or "", f"Status: {task.status}", f"Priority: {task.priority}"]
        if task.team and not task.team.is_personal:
            description_parts.append(f"Workspace: {task.team.name}")
        if task.assigned_to_id:
            description_parts.append(f"Assignee: {task.assigned_to.name or task.assigned_to.email}")
        description = "\n".join(part for part in description_parts if part)
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:worknest-task-{task.id}@worknest.app",
                f"DTSTAMP:{now_stamp}",
                f"DTSTART:{_to_ics_datetime(start_at)}",
                f"DTEND:{_to_ics_datetime(end_at)}",
                f"SUMMARY:{_ics_escape(task.title)}",
                f"DESCRIPTION:{_ics_escape(description)}",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)


def _parse_ics_datetime(*, value: str, is_date_only: bool = False) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None

    if is_date_only or len(raw) == 8:
        try:
            date_value = datetime.strptime(raw[:8], "%Y%m%d").date()
        except ValueError:
            return None
        return timezone.make_aware(datetime.combine(date_value, time(hour=9, minute=0)))

    parsed = parse_datetime(raw)
    if parsed is None:
        try:
            parsed = datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt_timezone.utc)
        except ValueError:
            try:
                parsed = datetime.strptime(raw, "%Y%m%dT%H%M%S")
            except ValueError:
                return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def parse_ics_payload(*, content: str) -> list[dict]:
    if not content or "BEGIN:VEVENT" not in content:
        return []

    raw_lines = content.splitlines()
    lines: list[str] = []
    for line in raw_lines:
        if (line.startswith(" ") or line.startswith("\t")) and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line.strip())

    entries: list[dict] = []
    current: dict | None = None
    for line in lines:
        upper = line.upper()
        if upper == "BEGIN:VEVENT":
            current = {}
            continue
        if upper == "END:VEVENT":
            if current is None:
                continue
            event_id = str(current.get("UID") or f"event-{len(entries) + 1}")
            summary = str(current.get("SUMMARY") or "").strip()
            description = str(current.get("DESCRIPTION") or "").replace("\\n", "\n").strip()
            start_raw = current.get("DTSTART", "")
            end_raw = current.get("DTEND", "")
            start_is_date = bool(current.get("DTSTART__DATE_ONLY", False))
            end_is_date = bool(current.get("DTEND__DATE_ONLY", False))
            start_at = _parse_ics_datetime(value=start_raw, is_date_only=start_is_date)
            end_at = _parse_ics_datetime(value=end_raw, is_date_only=end_is_date)
            if start_at and not end_at:
                end_at = start_at + timedelta(hours=1)
            entries.append(
                {
                    "event_id": event_id,
                    "summary": summary,
                    "description": description,
                    "start_at": start_at.isoformat() if start_at else None,
                    "end_at": end_at.isoformat() if end_at else None,
                    "is_valid": bool(summary and start_at),
                    "error": "" if summary and start_at else "Event is missing summary or start date.",
                }
            )
            current = None
            continue
        if current is None or ":" not in line:
            continue

        key, value = line.split(":", 1)
        key_parts = key.split(";")
        property_name = key_parts[0].upper()
        params = ";".join(key_parts[1:]).upper() if len(key_parts) > 1 else ""
        current[property_name] = value
        if property_name in {"DTSTART", "DTEND"} and "VALUE=DATE" in params:
            current[f"{property_name}__DATE_ONLY"] = True

    return entries


def create_import_batch(*, user, context: CalendarWorkspaceContext, source: str, events: list[dict]) -> CalendarImportBatch:
    return CalendarImportBatch.objects.create(
        user=user,
        team=context.team if context.scope == CalendarConnection.Scope.TEAM else None,
        scope=context.scope,
        source=source,
        payload={"events": events},
        expires_at=timezone.now() + timedelta(minutes=30),
    )


def _event_to_task_datetimes(event: dict) -> tuple[datetime | None, datetime | None]:
    start_at = parse_datetime(str(event.get("start_at") or "")) if event.get("start_at") else None
    due_date = parse_datetime(str(event.get("end_at") or "")) if event.get("end_at") else None
    if start_at and timezone.is_naive(start_at):
        start_at = timezone.make_aware(start_at, timezone.get_current_timezone())
    if due_date and timezone.is_naive(due_date):
        due_date = timezone.make_aware(due_date, timezone.get_current_timezone())
    if start_at and not due_date:
        due_date = start_at + timedelta(hours=1)
    return start_at, due_date


def confirm_import_batch(
    *,
    user,
    batch: CalendarImportBatch,
    import_all: bool,
    event_ids: list[str],
    default_status: str,
    default_priority: str,
    assign_to_me: bool = True,
) -> dict:
    if batch.user_id != user.id:
        raise PermissionDenied("You do not have access to this import batch.")
    if batch.is_expired:
        raise ValidationError({"batch_id": "This import batch has expired. Upload the calendar file again."})
    if batch.consumed_at is not None:
        raise ValidationError({"batch_id": "This import batch has already been used."})

    context = resolve_workspace_context(user=user, scope=batch.scope, team_id=batch.team_id)
    if context.scope == CalendarConnection.Scope.TEAM:
        ensure_team_manage_permission(context=context, action_label="import calendar events")

    source_events = list(batch.payload.get("events") or [])
    wanted = set(event_ids)
    chosen_events = [
        event
        for event in source_events
        if event.get("is_valid") and (import_all or str(event.get("event_id")) in wanted)
    ]

    created = 0
    skipped = 0
    skipped_reasons: list[dict] = []
    with transaction.atomic():
        for event in chosen_events:
            title = str(event.get("summary") or "").strip()
            if not title:
                skipped += 1
                skipped_reasons.append({"event_id": event.get("event_id"), "reason": "Missing title."})
                continue
            start_at, due_date = _event_to_task_datetimes(event)
            duplicate = Task.objects.filter(
                team=context.team,
                title__iexact=title,
                due_date=due_date,
                is_archived=False,
            ).exists()
            if duplicate:
                skipped += 1
                skipped_reasons.append({"event_id": event.get("event_id"), "reason": "Duplicate task already exists."})
                continue

            assigned_user = None
            if context.scope == CalendarConnection.Scope.TEAM and assign_to_me:
                assigned_user = user

            create_task(
                team=context.team,
                title=title,
                description=str(event.get("description") or "").strip(),
                status=default_status,
                priority=default_priority,
                start_at=start_at,
                due_date=due_date,
                created_by=user,
                assigned_to=assigned_user,
            )
            created += 1

        batch.consumed_at = timezone.now()
        batch.save(update_fields=["consumed_at", "updated_at"])

    return {
        "created_count": created,
        "skipped_count": skipped,
        "skipped": skipped_reasons,
        "selected_count": len(chosen_events),
    }


def _google_calendar_callback_url(request) -> str:
    configured = str(getattr(settings, "GOOGLE_CALENDAR_REDIRECT_URI", "")).strip()
    if configured:
        return configured
    backend_url = str(getattr(settings, "BACKEND_URL", "")).strip().rstrip("/")
    if not backend_url:
        backend_url = request.build_absolute_uri("/").rstrip("/")
    return f"{backend_url}/api/v1/calendar/google/callback/"


def build_google_calendar_oauth_url(
    *,
    request,
    user,
    context: CalendarWorkspaceContext,
    return_path: str = "",
) -> str:
    client_id = str(getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")).strip()
    client_secret = str(getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")).strip()
    if not client_id or not client_secret:
        raise ValidationError({"google": "Google OAuth credentials are not configured."})

    state_payload = {
        "uid": str(user.id),
        "scope": context.scope,
        "team_id": str(context.team.id) if context.scope == CalendarConnection.Scope.TEAM else "",
        "return_path": _safe_return_path(return_path),
    }
    state = signing.dumps(state_payload, salt=GOOGLE_OAUTH_STATE_SALT)
    params = {
        "client_id": client_id,
        "redirect_uri": _google_calendar_callback_url(request),
        "response_type": "code",
        "scope": "openid email https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/calendar.events",
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def parse_google_calendar_state(*, raw_state: str) -> dict:
    try:
        payload = signing.loads(raw_state, salt=GOOGLE_OAUTH_STATE_SALT, max_age=900)
    except signing.BadSignature as exc:
        raise ValidationError({"state": "Google calendar state is invalid or expired."}) from exc
    if not isinstance(payload, dict):
        raise ValidationError({"state": "Google calendar state is invalid."})
    return payload


def _google_token_exchange(*, code: str, redirect_uri: str) -> dict:
    import requests

    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": str(getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")).strip(),
            "client_secret": str(getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")).strip(),
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        timeout=_google_timeout_seconds(),
    )
    if response.status_code >= 400:
        try:
            payload = response.json()
        except ValueError:
            payload = {"detail": response.text}
        raise ValidationError({"google": payload.get("error_description") or payload.get("error") or "Google token exchange failed."})
    return response.json()


def _google_refresh_access_token(*, refresh_token: str) -> dict:
    import requests

    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "refresh_token": refresh_token,
            "client_id": str(getattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "")).strip(),
            "client_secret": str(getattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "")).strip(),
            "grant_type": "refresh_token",
        },
        timeout=_google_timeout_seconds(),
    )
    if response.status_code >= 400:
        try:
            payload = response.json()
        except ValueError:
            payload = {"detail": response.text}
        raise ValidationError({"google": payload.get("error_description") or payload.get("error") or "Failed to refresh Google token."})
    return response.json()


def _resolve_token_expiry(expires_in: int | str | None):
    try:
        seconds = max(30, int(expires_in or 0))
    except (TypeError, ValueError):
        seconds = 3600
    return timezone.now() + timedelta(seconds=seconds)


def upsert_google_connection(
    *,
    user,
    context: CalendarWorkspaceContext,
    token_payload: dict,
    calendar_id: str = "",
    calendar_name: str = "",
) -> CalendarConnection:
    connection, _created = CalendarConnection.objects.get_or_create(
        user=user,
        team=context.team if context.scope == CalendarConnection.Scope.TEAM else None,
        scope=context.scope,
        provider=OAUTH_PROVIDER_GOOGLE,
        defaults={
            "status": CalendarConnection.Status.CONNECTED,
        },
    )

    access_token = str(token_payload.get("access_token") or "").strip()
    refresh_token = str(token_payload.get("refresh_token") or "").strip()
    if not access_token:
        raise ValidationError({"google": "Google token payload did not include an access token."})

    if refresh_token:
        connection.refresh_token = refresh_token
    connection.access_token = access_token
    connection.status = CalendarConnection.Status.CONNECTED
    connection.token_expires_at = _resolve_token_expiry(token_payload.get("expires_in"))
    connection.last_error = ""
    if calendar_id:
        connection.external_calendar_id = calendar_id
        connection.external_calendar_name = calendar_name or connection.external_calendar_name
    connection.save(
        update_fields=[
            "access_token",
            "refresh_token",
            "status",
            "token_expires_at",
            "last_error",
            "external_calendar_id",
            "external_calendar_name",
            "updated_at",
        ]
    )
    return connection


def get_google_connection_for_context(*, user, context: CalendarWorkspaceContext) -> CalendarConnection | None:
    return CalendarConnection.objects.filter(
        user=user,
        team=context.team if context.scope == CalendarConnection.Scope.TEAM else None,
        scope=context.scope,
        provider=OAUTH_PROVIDER_GOOGLE,
    ).first()


def _ensure_google_connection_access_token(*, connection: CalendarConnection) -> CalendarConnection:
    if connection.status != CalendarConnection.Status.CONNECTED:
        raise ValidationError({"google": "Google Calendar is not connected for this workspace."})
    if not connection.access_token and not connection.refresh_token:
        raise ValidationError({"google": "Google connection is missing credentials. Reconnect and try again."})

    if connection.token_expires_at and connection.token_expires_at > timezone.now() + timedelta(seconds=30):
        return connection
    if not connection.refresh_token:
        return connection

    refreshed = _google_refresh_access_token(refresh_token=connection.refresh_token)
    access_token = str(refreshed.get("access_token") or "").strip()
    if not access_token:
        raise ValidationError({"google": "Unable to refresh Google access token."})
    connection.access_token = access_token
    connection.token_expires_at = _resolve_token_expiry(refreshed.get("expires_in"))
    connection.status = CalendarConnection.Status.CONNECTED
    connection.last_error = ""
    connection.save(update_fields=["access_token", "token_expires_at", "status", "last_error", "updated_at"])
    return connection


def _google_api_request(*, connection: CalendarConnection, method: str, path: str, params=None, json_body=None) -> dict:
    import requests

    connection = _ensure_google_connection_access_token(connection=connection)
    url = f"https://www.googleapis.com/calendar/v3/{path.lstrip('/')}"
    headers = {"Authorization": f"Bearer {connection.access_token}"}
    response = requests.request(
        method.upper(),
        url,
        params=params,
        json=json_body,
        headers=headers,
        timeout=_google_timeout_seconds(),
    )

    if response.status_code == 401 and connection.refresh_token:
        connection = _ensure_google_connection_access_token(connection=connection)
        headers["Authorization"] = f"Bearer {connection.access_token}"
        response = requests.request(
            method.upper(),
            url,
            params=params,
            json=json_body,
            headers=headers,
            timeout=_google_timeout_seconds(),
        )

    if response.status_code >= 400:
        try:
            payload = response.json()
        except ValueError:
            payload = {"detail": response.text}
        detail = payload.get("error", {}).get("message") if isinstance(payload.get("error"), dict) else payload.get("error")
        detail = detail or payload.get("detail") or "Google Calendar request failed."
        raise ValidationError({"google": detail})

    if not response.text:
        return {}
    try:
        return response.json()
    except ValueError:
        return {}


def list_google_calendars(*, connection: CalendarConnection) -> list[dict]:
    payload = _google_api_request(connection=connection, method="GET", path="users/me/calendarList", params={"maxResults": 250})
    calendars = []
    for item in payload.get("items", []) or []:
        calendars.append(
            {
                "id": item.get("id"),
                "summary": item.get("summary"),
                "primary": bool(item.get("primary")),
                "access_role": item.get("accessRole"),
                "time_zone": item.get("timeZone"),
                "selected": str(item.get("id", "")) == str(connection.external_calendar_id or ""),
            }
        )
    return calendars


def set_google_calendar_selection(*, connection: CalendarConnection, calendar_id: str, calendar_name: str = "") -> CalendarConnection:
    connection.external_calendar_id = calendar_id.strip()
    if calendar_name.strip():
        connection.external_calendar_name = calendar_name.strip()
    connection.save(update_fields=["external_calendar_id", "external_calendar_name", "updated_at"])
    return connection


def disconnect_google_calendar(*, connection: CalendarConnection) -> CalendarConnection:
    connection.status = CalendarConnection.Status.DISCONNECTED
    connection.access_token = ""
    connection.refresh_token = ""
    connection.token_expires_at = None
    connection.last_error = ""
    connection.save(update_fields=["status", "access_token", "refresh_token", "token_expires_at", "last_error", "updated_at"])
    return connection


def _task_to_google_event_payload(task: Task) -> dict:
    start_at = task.start_at or task.due_date or timezone.now()
    due_date = task.due_date or (start_at + timedelta(hours=1))
    if timezone.is_naive(start_at):
        start_at = timezone.make_aware(start_at, timezone.get_current_timezone())
    if timezone.is_naive(due_date):
        due_date = timezone.make_aware(due_date, timezone.get_current_timezone())

    lines = []
    if task.description:
        lines.append(task.description.strip())
    lines.append(f"Status: {task.status}")
    lines.append(f"Priority: {task.priority}")
    if task.team and not task.team.is_personal:
        lines.append(f"Workspace: {task.team.name}")
    if task.assigned_to_id:
        lines.append(f"Assignee: {task.assigned_to.name or task.assigned_to.email}")
    description = "\n".join(line for line in lines if line)

    return {
        "summary": task.title,
        "description": description,
        "start": {"dateTime": start_at.astimezone(dt_timezone.utc).isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": due_date.astimezone(dt_timezone.utc).isoformat(), "timeZone": "UTC"},
    }


def sync_tasks_to_google_calendar(*, connection: CalendarConnection, tasks: Iterable[Task]) -> dict:
    calendar_id = str(connection.external_calendar_id or "").strip() or "primary"
    created = 0
    updated = 0
    failed = 0
    failures: list[dict] = []

    for task in tasks:
        payload = _task_to_google_event_payload(task)
        binding = CalendarEventBinding.objects.filter(connection=connection, task=task).first()
        try:
            if binding and binding.external_event_id:
                event_payload = _google_api_request(
                    connection=connection,
                    method="PATCH",
                    path=f"calendars/{calendar_id}/events/{binding.external_event_id}",
                    json_body=payload,
                )
                updated += 1
            else:
                event_payload = _google_api_request(
                    connection=connection,
                    method="POST",
                    path=f"calendars/{calendar_id}/events",
                    json_body=payload,
                )
                created += 1

            external_event_id = str(
                event_payload.get("id") or (binding.external_event_id if binding else "")
            ).strip()
            if not external_event_id:
                raise ValidationError({"google": "Google did not return an event ID."})

            CalendarEventBinding.objects.update_or_create(
                connection=connection,
                task=task,
                defaults={
                    "external_event_id": external_event_id,
                    "external_calendar_id": calendar_id,
                    "etag": str(event_payload.get("etag") or ""),
                    "sync_status": CalendarEventBinding.SyncStatus.SYNCED,
                    "last_synced_at": timezone.now(),
                    "last_error": "",
                    "metadata": {
                        "html_link": event_payload.get("htmlLink", ""),
                        "updated": event_payload.get("updated", ""),
                    },
                },
            )
        except Exception as exc:
            failed += 1
            failures.append({"task_id": str(task.id), "title": task.title, "error": str(exc)})
            if binding:
                binding.sync_status = CalendarEventBinding.SyncStatus.FAILED
                binding.last_error = str(exc)
                binding.last_synced_at = timezone.now()
                binding.save(update_fields=["sync_status", "last_error", "last_synced_at", "updated_at"])

    connection.last_synced_at = timezone.now()
    connection.last_error = failures[0]["error"] if failures else ""
    connection.save(update_fields=["last_synced_at", "last_error", "updated_at"])
    return {
        "created_events": created,
        "updated_events": updated,
        "failed_events": failed,
        "failures": failures,
    }


def fetch_google_calendar_events_preview(
    *,
    connection: CalendarConnection,
    max_results: int = 50,
    time_min: datetime | None = None,
    time_max: datetime | None = None,
) -> list[dict]:
    calendar_id = str(connection.external_calendar_id or "").strip() or "primary"
    params = {
        "maxResults": max_results,
        "singleEvents": "true",
        "orderBy": "startTime",
    }
    if time_min:
        if timezone.is_naive(time_min):
            time_min = timezone.make_aware(time_min, timezone.get_current_timezone())
        params["timeMin"] = time_min.astimezone(dt_timezone.utc).isoformat()
    if time_max:
        if timezone.is_naive(time_max):
            time_max = timezone.make_aware(time_max, timezone.get_current_timezone())
        params["timeMax"] = time_max.astimezone(dt_timezone.utc).isoformat()

    payload = _google_api_request(
        connection=connection,
        method="GET",
        path=f"calendars/{calendar_id}/events",
        params=params,
    )

    events: list[dict] = []
    for item in payload.get("items", []) or []:
        start = item.get("start") or {}
        end = item.get("end") or {}
        start_at = start.get("dateTime") or start.get("date")
        end_at = end.get("dateTime") or end.get("date")
        events.append(
            {
                "event_id": str(item.get("id") or ""),
                "summary": str(item.get("summary") or "Imported event"),
                "description": str(item.get("description") or ""),
                "start_at": start_at,
                "end_at": end_at,
                "is_valid": bool(start_at),
                "error": "" if start_at else "Event has no start date.",
                "source": "google",
            }
        )
    return events


def build_google_connection_status_payload(*, connection: CalendarConnection | None, context: CalendarWorkspaceContext) -> dict:
    if not connection:
        return {
            "connected": False,
            "scope": context.scope,
            "team_id": str(context.team.id) if context.scope == CalendarConnection.Scope.TEAM else None,
            "calendar_id": "",
            "calendar_name": "",
            "last_synced_at": None,
            "status": CalendarConnection.Status.DISCONNECTED,
            "can_manage": context.can_manage_team_calendar,
        }
    return {
        "connected": connection.status == CalendarConnection.Status.CONNECTED,
        "scope": connection.scope,
        "team_id": str(connection.team_id) if connection.team_id else None,
        "calendar_id": connection.external_calendar_id,
        "calendar_name": connection.external_calendar_name,
        "last_synced_at": connection.last_synced_at,
        "status": connection.status,
        "last_error": connection.last_error,
        "can_manage": context.can_manage_team_calendar,
    }
