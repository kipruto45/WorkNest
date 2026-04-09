from __future__ import annotations

from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from apps.common.responses import success_response
from apps.integrations.email.builders import _get_frontend_url
from apps.integrations.calendar_serializers import (
    CalendarImportConfirmSerializer,
    CalendarImportPreviewSerializer,
    CalendarTaskSelectionSerializer,
    GoogleCalendarConnectSerializer,
    GoogleCalendarImportPreviewSerializer,
    GoogleCalendarSelectSerializer,
    GoogleCalendarSyncSerializer,
)
from apps.integrations.calendar_services import (
    _google_calendar_callback_url,
    _google_token_exchange,
    build_google_calendar_oauth_url,
    build_google_connection_status_payload,
    build_ics_content,
    build_task_queryset_for_context,
    confirm_import_batch,
    create_import_batch,
    disconnect_google_calendar,
    ensure_team_manage_permission,
    fetch_google_calendar_events_preview,
    get_google_connection_for_context,
    list_google_calendars,
    parse_google_calendar_state,
    parse_ics_payload,
    resolve_workspace_context,
    set_google_calendar_selection,
    sync_tasks_to_google_calendar,
    upsert_google_connection,
)
from apps.integrations.models import CalendarConnection, CalendarImportBatch
from apps.tasks.models import Task

User = get_user_model()


def _frontend_redirect_url(*, return_path: str = "", params: dict | None = None) -> str:
    frontend_url = _get_frontend_url().rstrip("/")
    path = return_path if return_path.startswith("/") else "/settings"
    query = urlencode(params or {})
    if frontend_url:
        return f"{frontend_url}{path}{f'?{query}' if query else ''}"
    return f"{path}{f'?{query}' if query else ''}"


class CalendarTaskExportICSView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=CalendarTaskSelectionSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = CalendarTaskSelectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        context = resolve_workspace_context(
            user=request.user,
            scope=data["scope"],
            team_id=data.get("team_id"),
        )
        queryset = build_task_queryset_for_context(
            user=request.user,
            context=context,
            filters={
                "task_ids": data.get("task_ids"),
                "include_my_tasks": data.get("include_my_tasks", False),
                "status": data.get("status"),
                "priority": data.get("priority"),
                "assigned_to": data.get("assigned_to"),
                "due_from": data.get("due_from"),
                "due_to": data.get("due_to"),
                "start_from": data.get("start_from"),
                "start_to": data.get("start_to"),
                "search": data.get("search", ""),
                "include_completed": data.get("include_completed", True),
            },
        )
        tasks = list(queryset)
        calendar_name = context.team.name if context.scope == CalendarConnection.Scope.TEAM else "Personal Tasks"
        ics_content = build_ics_content(tasks=tasks, calendar_name=calendar_name)
        workspace_slug = "personal" if context.scope == CalendarConnection.Scope.PERSONAL else context.team.slug
        return success_response(
            request=request,
            message="Calendar export generated successfully.",
            data={
                "content": ics_content,
                "filename": f"{workspace_slug}-tasks.ics",
                "count": len(tasks),
                "scope": context.scope,
                "team_id": str(context.team.id) if context.scope == CalendarConnection.Scope.TEAM else None,
            },
        )


class CalendarImportPreviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(request=CalendarImportPreviewSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = CalendarImportPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        context = resolve_workspace_context(
            user=request.user,
            scope=serializer.validated_data["scope"],
            team_id=serializer.validated_data.get("team_id"),
        )
        if context.scope == CalendarConnection.Scope.TEAM:
            ensure_team_manage_permission(context=context, action_label="import ICS tasks")

        upload = request.FILES.get("file")
        if not upload:
            raise ValidationError({"file": "ICS file is required."})
        content = upload.read().decode("utf-8", errors="ignore")
        events = parse_ics_payload(content=content)
        duplicates = 0
        for event in events:
            if not event.get("is_valid"):
                continue
            due_date = parse_datetime(str(event.get("end_at") or "")) if event.get("end_at") else None
            if due_date and timezone.is_naive(due_date):
                due_date = timezone.make_aware(due_date, timezone.get_current_timezone())
            duplicate_exists = Task.objects.filter(
                team=context.team,
                title__iexact=str(event.get("summary") or "").strip(),
                due_date=due_date,
                is_archived=False,
            ).exists()
            if duplicate_exists:
                event["duplicate"] = True
                duplicates += 1
            else:
                event["duplicate"] = False

        batch = create_import_batch(
            user=request.user,
            context=context,
            source=CalendarImportBatch.Source.ICS,
            events=events,
        )
        return success_response(
            request=request,
            message="Calendar import preview generated successfully.",
            data={
                "batch_id": str(batch.id),
                "events": events,
                "summary": {
                    "total": len(events),
                    "valid": len([event for event in events if event.get("is_valid")]),
                    "duplicates": duplicates,
                },
                "expires_at": batch.expires_at,
            },
        )


class CalendarImportConfirmView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=CalendarImportConfirmSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = CalendarImportConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        batch = CalendarImportBatch.objects.filter(id=data["batch_id"]).first()
        if not batch:
            raise ValidationError({"batch_id": "Import batch not found."})
        result = confirm_import_batch(
            user=request.user,
            batch=batch,
            import_all=data["import_all"],
            event_ids=data.get("event_ids") or [],
            default_status=data.get("default_status", Task.Status.TODO),
            default_priority=data.get("default_priority", Task.Priority.MEDIUM),
            assign_to_me=data.get("assign_to_me", True),
        )
        return success_response(
            request=request,
            message="Calendar events imported successfully.",
            data=result,
        )


class GoogleCalendarConnectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=GoogleCalendarConnectSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = GoogleCalendarConnectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        context = resolve_workspace_context(user=request.user, scope=data["scope"], team_id=data.get("team_id"))
        if context.scope == CalendarConnection.Scope.TEAM:
            ensure_team_manage_permission(context=context, action_label="connect Google Calendar")

        auth_url = build_google_calendar_oauth_url(
            request=request,
            user=request.user,
            context=context,
            return_path=data.get("return_path", ""),
        )
        return success_response(
            request=request,
            message="Google Calendar authorization URL generated successfully.",
            data={"authorization_url": auth_url},
        )


class GoogleCalendarCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        raw_state = str(request.query_params.get("state") or "").strip()
        code = str(request.query_params.get("code") or "").strip()
        error = str(request.query_params.get("error") or "").strip()

        if not raw_state:
            return HttpResponseRedirect(_frontend_redirect_url(params={"calendar_sync": "failed", "reason": "missing_state"}))

        try:
            state = parse_google_calendar_state(raw_state=raw_state)
            user = User.objects.filter(id=state.get("uid")).first()
            if not user:
                raise ValidationError({"state": "Invalid user in OAuth state."})

            context = resolve_workspace_context(
                user=user,
                scope=str(state.get("scope") or CalendarConnection.Scope.PERSONAL),
                team_id=state.get("team_id") or None,
            )
            if context.scope == CalendarConnection.Scope.TEAM:
                ensure_team_manage_permission(context=context, action_label="connect Google Calendar")

            return_path = str(state.get("return_path") or "")
            default_path = f"/teams/{context.team.id}/calendar" if context.scope == CalendarConnection.Scope.TEAM else "/calendar"
            redirect_path = return_path if return_path.startswith("/") else default_path

            if error:
                return HttpResponseRedirect(
                    _frontend_redirect_url(
                        return_path=redirect_path,
                        params={"calendar_sync": "failed", "reason": error},
                    )
                )
            if not code:
                return HttpResponseRedirect(
                    _frontend_redirect_url(
                        return_path=redirect_path,
                        params={"calendar_sync": "failed", "reason": "missing_code"},
                    )
                )

            token_payload = _google_token_exchange(code=code, redirect_uri=_google_calendar_callback_url(request))
            upsert_google_connection(user=user, context=context, token_payload=token_payload)
            return HttpResponseRedirect(
                _frontend_redirect_url(
                    return_path=redirect_path,
                    params={
                        "calendar_sync": "connected",
                        "scope": context.scope,
                        "team_id": str(context.team.id) if context.scope == CalendarConnection.Scope.TEAM else "",
                    },
                )
            )
        except Exception as exc:
            return HttpResponseRedirect(
                _frontend_redirect_url(
                    params={"calendar_sync": "failed", "reason": str(exc)[:120]},
                )
            )


class GoogleCalendarStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=GoogleCalendarConnectSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = GoogleCalendarConnectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        context = resolve_workspace_context(user=request.user, scope=data["scope"], team_id=data.get("team_id"))
        connection = get_google_connection_for_context(user=request.user, context=context)
        return success_response(
            request=request,
            message="Google Calendar status retrieved successfully.",
            data=build_google_connection_status_payload(connection=connection, context=context),
        )


class GoogleCalendarListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=GoogleCalendarConnectSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = GoogleCalendarConnectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        context = resolve_workspace_context(user=request.user, scope=data["scope"], team_id=data.get("team_id"))
        if context.scope == CalendarConnection.Scope.TEAM:
            ensure_team_manage_permission(context=context, action_label="list Google calendars")

        connection = get_google_connection_for_context(user=request.user, context=context)
        if not connection:
            raise ValidationError({"google": "Google Calendar is not connected for this workspace."})
        calendars = list_google_calendars(connection=connection)
        return success_response(
            request=request,
            message="Google Calendar list retrieved successfully.",
            data={"calendars": calendars},
        )


class GoogleCalendarSelectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=GoogleCalendarSelectSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = GoogleCalendarSelectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        context = resolve_workspace_context(user=request.user, scope=data["scope"], team_id=data.get("team_id"))
        if context.scope == CalendarConnection.Scope.TEAM:
            ensure_team_manage_permission(context=context, action_label="update team calendar selection")

        connection = get_google_connection_for_context(user=request.user, context=context)
        if not connection:
            raise ValidationError({"google": "Google Calendar is not connected for this workspace."})
        connection = set_google_calendar_selection(
            connection=connection,
            calendar_id=data["calendar_id"],
            calendar_name=data.get("calendar_name", ""),
        )
        return success_response(
            request=request,
            message="Google Calendar target updated successfully.",
            data=build_google_connection_status_payload(connection=connection, context=context),
        )


class GoogleCalendarDisconnectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=GoogleCalendarConnectSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = GoogleCalendarConnectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        context = resolve_workspace_context(user=request.user, scope=data["scope"], team_id=data.get("team_id"))
        if context.scope == CalendarConnection.Scope.TEAM:
            ensure_team_manage_permission(context=context, action_label="disconnect Google Calendar")

        connection = get_google_connection_for_context(user=request.user, context=context)
        if not connection:
            return success_response(
                request=request,
                message="Google Calendar was already disconnected.",
                data=build_google_connection_status_payload(connection=None, context=context),
            )
        disconnect_google_calendar(connection=connection)
        return success_response(
            request=request,
            message="Google Calendar disconnected successfully.",
            data=build_google_connection_status_payload(connection=connection, context=context),
        )


class GoogleCalendarSyncTasksView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=GoogleCalendarSyncSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = GoogleCalendarSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        context = resolve_workspace_context(user=request.user, scope=data["scope"], team_id=data.get("team_id"))
        if context.scope == CalendarConnection.Scope.TEAM:
            ensure_team_manage_permission(context=context, action_label="sync team tasks")

        connection = get_google_connection_for_context(user=request.user, context=context)
        if not connection:
            raise ValidationError({"google": "Google Calendar is not connected for this workspace."})
        if data.get("calendar_id"):
            connection = set_google_calendar_selection(
                connection=connection,
                calendar_id=data["calendar_id"],
                calendar_name="",
            )

        tasks = list(
            build_task_queryset_for_context(
                user=request.user,
                context=context,
                filters={
                    "task_ids": data.get("task_ids"),
                    "include_my_tasks": data.get("include_my_tasks", False),
                    "status": data.get("status"),
                    "priority": data.get("priority"),
                    "assigned_to": data.get("assigned_to"),
                    "due_from": data.get("due_from"),
                    "due_to": data.get("due_to"),
                    "start_from": data.get("start_from"),
                    "start_to": data.get("start_to"),
                    "search": data.get("search", ""),
                    "include_completed": data.get("include_completed", True),
                },
            )
        )
        stats = sync_tasks_to_google_calendar(connection=connection, tasks=tasks)
        return success_response(
            request=request,
            message="Google Calendar sync completed.",
            data={
                "synced_task_count": len(tasks),
                **stats,
            },
        )


class GoogleCalendarImportPreviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=GoogleCalendarImportPreviewSerializer)
    def post(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = GoogleCalendarImportPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        context = resolve_workspace_context(user=request.user, scope=data["scope"], team_id=data.get("team_id"))
        if context.scope == CalendarConnection.Scope.TEAM:
            ensure_team_manage_permission(context=context, action_label="import Google Calendar events")

        connection = get_google_connection_for_context(user=request.user, context=context)
        if not connection:
            raise ValidationError({"google": "Google Calendar is not connected for this workspace."})

        events = fetch_google_calendar_events_preview(
            connection=connection,
            max_results=data.get("max_results", 50),
            time_min=data.get("time_min"),
            time_max=data.get("time_max"),
        )
        batch = create_import_batch(
            user=request.user,
            context=context,
            source=CalendarImportBatch.Source.GOOGLE,
            events=events,
        )
        return success_response(
            request=request,
            message="Google Calendar import preview generated successfully.",
            data={
                "batch_id": str(batch.id),
                "events": events,
                "summary": {
                    "total": len(events),
                    "valid": len([event for event in events if event.get("is_valid")]),
                },
                "expires_at": batch.expires_at,
            },
        )
