from __future__ import annotations

from django.conf import settings
from django.db.models import Case, IntegerField, Prefetch, Q, Value, When
from django.http import JsonResponse
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.views import APIView

from apps.comments.models import Comment
from apps.common.constants import API_NAME, HEALTH_STATUS_DEGRADED, HEALTH_STATUS_OK
from apps.common.health import get_cache_health, get_database_health
from apps.common.responses import success_response
from apps.common.utils import get_api_version, get_runtime_environment
from apps.memberships.models import Membership
from apps.tasks.models import Milestone, RecentTaskVisit, Task
from apps.tasks.selectors import get_user_membership_tasks
from apps.teams.models import RecentTeamVisit, Team, TeamAnnouncement
from apps.teams.selectors import get_user_teams
from apps.users.models import User
from apps.users.serializers import UserPublicSerializer


class APIRootView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses=inline_serializer(
            name="APIRootResponse",
            fields={
                "name": serializers.CharField(),
                "version": serializers.CharField(),
                "environment": serializers.CharField(),
                "docs": serializers.DictField(child=serializers.URLField()),
                "system": serializers.DictField(child=serializers.URLField()),
            },
        )
    )
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        return success_response(
            request=request,
            message="API root loaded successfully.",
            data={
                "name": API_NAME,
                "version": get_api_version(),
                "environment": get_runtime_environment(),
                "docs": {
                    "schema": request.build_absolute_uri("/api/v1/schema/"),
                    "swagger": request.build_absolute_uri("/api/v1/docs/"),
                    "redoc": request.build_absolute_uri("/api/v1/docs/redoc/"),
                },
                "system": {
                    "health": request.build_absolute_uri("/api/v1/health/"),
                    "health_live": request.build_absolute_uri("/api/v1/health/live/"),
                    "health_ready": request.build_absolute_uri("/api/v1/health/ready/"),
                    "info": request.build_absolute_uri("/api/v1/system/info/"),
                },
            },
        )


class HealthCheckView(APIView):
    permission_classes = [permissions.AllowAny]

    @staticmethod
    def _json_probe_response(*, request, message: str, data: dict, status_code: int = 200) -> JsonResponse:
        return JsonResponse(
            {
                "success": True,
                "message": message,
                "request_id": getattr(request, "request_id", None),
                "data": data,
            },
            status=status_code,
        )

    @staticmethod
    def _build_dependency_snapshot() -> tuple[str, str]:
        try:
            database_status = get_database_health()
        except Exception:
            database_status = "unavailable"

        try:
            cache_status = get_cache_health()
        except Exception:
            cache_status = "unavailable"

        return database_status, cache_status

    @extend_schema(
        responses=inline_serializer(
            name="HealthCheckResponse",
            fields={
                "status": serializers.CharField(),
                "environment": serializers.CharField(),
                "services": serializers.DictField(child=serializers.CharField()),
            },
        )
    )
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        try:
            probe = kwargs.get("probe", "full")
            if probe == "live":
                return self._json_probe_response(
                    request=request,
                    message="Liveness probe completed.",
                    data={
                        "status": "ok",
                        "environment": getattr(settings, "ENVIRONMENT", "production"),
                        "services": {
                            "application": "ok",
                        },
                    },
                )

            database_status, cache_status = self._build_dependency_snapshot()
            cache_is_required = bool(getattr(settings, "HEALTH_REQUIRE_CACHE", False))
            database_ok = database_status == "ok"
            cache_ok = cache_status == "ok"
            response_status = (
                status.HTTP_200_OK
                if database_ok and (cache_ok or not cache_is_required)
                else status.HTTP_503_SERVICE_UNAVAILABLE
            )

            return self._json_probe_response(
                request=request,
                message="Readiness probe completed." if probe == "ready" else "Healthcheck completed.",
                data={
                    "status": HEALTH_STATUS_OK if response_status == status.HTTP_200_OK else HEALTH_STATUS_DEGRADED,
                    "environment": get_runtime_environment(),
                    "services": {
                        "database": database_status,
                        "redis": cache_status,
                        "channels": "configured",
                        "celery": "configured",
                    },
                },
                status_code=response_status,
            )
        except Exception:
            return self._json_probe_response(
                request=request,
                message="Readiness probe completed with degraded dependencies.",
                data={
                    "status": HEALTH_STATUS_DEGRADED,
                    "environment": get_runtime_environment(),
                    "services": {
                        "database": "unknown",
                        "redis": "unknown",
                        "channels": "configured",
                        "celery": "configured",
                    },
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class SystemInfoView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses=inline_serializer(
            name="SystemInfoResponse",
            fields={
                "version": serializers.CharField(),
                "environment": serializers.CharField(),
                "debug": serializers.BooleanField(),
                "docs_enabled": serializers.BooleanField(),
            },
        )
    )
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        return success_response(
            request=request,
            message="System information retrieved successfully.",
            data={
                "version": get_api_version(),
                "environment": get_runtime_environment(),
                "debug": settings.DEBUG,
                "docs_enabled": True,
            },
        )


class GlobalSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        query = str(request.query_params.get("q", "")).strip()
        limit = min(max(int(request.query_params.get("limit", 6) or 6), 1), 20)
        types_param = str(request.query_params.get("types", "")).strip()
        types = {value.strip() for value in types_param.split(",") if value.strip()} or {
            "tasks",
            "teams",
            "people",
            "comments",
            "announcements",
            "milestones",
        }
        team_id = request.query_params.get("team")
        assignee_id = request.query_params.get("assignee")
        status_filter = request.query_params.get("status")
        priority_filter = request.query_params.get("priority")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        milestone_id = request.query_params.get("milestone")
        label_id = request.query_params.get("label")

        if query:
            tasks_queryset = get_user_membership_tasks(request.user).filter(Q(title__icontains=query) | Q(description__icontains=query))
            if team_id:
                tasks_queryset = tasks_queryset.filter(team_id=team_id)
            if assignee_id:
                tasks_queryset = tasks_queryset.filter(assigned_to_id=assignee_id)
            if status_filter:
                tasks_queryset = tasks_queryset.filter(status=status_filter)
            if priority_filter:
                tasks_queryset = tasks_queryset.filter(priority=priority_filter)
            if date_from:
                tasks_queryset = tasks_queryset.filter(due_date__date__gte=date_from)
            if date_to:
                tasks_queryset = tasks_queryset.filter(due_date__date__lte=date_to)
            if milestone_id:
                tasks_queryset = tasks_queryset.filter(milestone_id=milestone_id)
            if label_id:
                tasks_queryset = tasks_queryset.filter(labels__id=label_id)

            tasks = (
                list(
                    tasks_queryset.annotate(
                        rank=Case(
                            When(title__iexact=query, then=Value(0)),
                            When(title__istartswith=query, then=Value(1)),
                            default=Value(2),
                            output_field=IntegerField(),
                        )
                    )
                    .order_by("rank", "-updated_at")[:limit]
                )
                if "tasks" in types
                else []
            )
            teams = (
                list(
                    get_user_teams(user=request.user)
                    .filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(slug__icontains=query))
                    .annotate(
                        rank=Case(
                            When(name__iexact=query, then=Value(0)),
                            When(name__istartswith=query, then=Value(1)),
                            default=Value(2),
                            output_field=IntegerField(),
                        )
                    )
                    .order_by("rank", "name")[:limit]
                )
                if "teams" in types
                else []
            )
            comments = (
                list(
                    Comment.objects.select_related("task", "author")
                    .filter(
                        task__team__memberships__user=request.user,
                        task__team__memberships__status=Membership.Status.ACTIVE,
                        is_deleted=False,
                        content__icontains=query,
                    )
                    .order_by("-updated_at")[:limit]
                )
                if "comments" in types
                else []
            )
            people = (
                list(
                    User.objects.filter(
                        team_memberships__team__memberships__user=request.user,
                        team_memberships__status=Membership.Status.ACTIVE,
                        is_active=True,
                    )
                    .filter(Q(name__icontains=query) | Q(email__icontains=query))
                    .distinct()
                    .order_by("name", "email")[:limit]
                )
                if "people" in types
                else []
            )
            announcements = (
                list(
                    TeamAnnouncement.objects.select_related("team", "published_by")
                    .filter(
                        team__memberships__user=request.user,
                        team__memberships__status=Membership.Status.ACTIVE,
                        is_active=True,
                    )
                    .filter(Q(title__icontains=query) | Q(content__icontains=query))
                    .order_by("-created_at")[:limit]
                )
                if "announcements" in types
                else []
            )
            milestones = (
                list(
                    Milestone.objects.select_related("team", "created_by")
                    .filter(
                        team__memberships__user=request.user,
                        team__memberships__status=Membership.Status.ACTIVE,
                    )
                    .filter(Q(title__icontains=query) | Q(description__icontains=query))
                    .order_by("due_date", "-created_at")[:limit]
                )
                if "milestones" in types
                else []
            )
        else:
            recent_task_ids = list(
                RecentTaskVisit.objects.filter(user=request.user).order_by("-last_accessed_at").values_list("task_id", flat=True)[:limit]
            )
            recent_team_ids = list(
                RecentTeamVisit.objects.filter(user=request.user).order_by("-last_accessed_at").values_list("team_id", flat=True)[:limit]
            )
            tasks = list(Task.objects.filter(id__in=recent_task_ids)) if "tasks" in types else []
            teams = list(Team.objects.filter(id__in=recent_team_ids)) if "teams" in types else []
            comments = [] if "comments" in types else []
            people = [] if "people" in types else []
            announcements = (
                list(
                    TeamAnnouncement.objects.select_related("team", "published_by")
                    .filter(team__memberships__user=request.user, team__memberships__status=Membership.Status.ACTIVE, is_active=True)
                    .order_by("-created_at")[:limit]
                )
                if "announcements" in types
                else []
            )
            milestones = (
                list(
                    Milestone.objects.select_related("team", "created_by")
                    .filter(
                        team__memberships__user=request.user,
                        team__memberships__status=Membership.Status.ACTIVE,
                    )
                    .order_by("due_date", "-created_at")[:limit]
                )
                if "milestones" in types
                else []
            )

        return success_response(
            request=request,
            message="Search results retrieved successfully.",
            data={
                "query": query,
                "sections": {
                    "tasks": [
                        {
                            "id": str(task.id),
                            "title": task.title,
                            "subtitle": task.team.name,
                            "href": f"/tasks/{task.id}",
                            "status": task.status,
                            "priority": task.priority,
                            "type": "task",
                        }
                        for task in tasks
                    ],
                    "teams": [
                        {
                            "id": str(team.id),
                            "title": team.name,
                            "subtitle": team.description,
                            "href": f"/teams/{team.id}/overview",
                            "type": "team",
                        }
                        for team in teams
                    ],
                    "comments": [
                        {
                            "id": str(comment.id),
                            "title": comment.content[:120],
                            "subtitle": comment.task.title,
                            "href": f"/tasks/{comment.task_id}?comment={comment.id}",
                            "type": "comment",
                        }
                        for comment in comments
                    ],
                    "people": [
                        {
                            "id": str(person.id),
                            "title": person.name or person.email,
                            "subtitle": person.email,
                            "href": f"/profile?user={person.id}",
                            "type": "user",
                            "presence": UserPublicSerializer(person).data.get("presence"),
                        }
                        for person in people
                    ],
                    "announcements": [
                        {
                            "id": str(announcement.id),
                            "title": announcement.title,
                            "subtitle": announcement.team.name,
                            "href": f"/teams/{announcement.team_id}/overview?announcement={announcement.id}",
                            "type": "announcement",
                        }
                        for announcement in announcements
                    ],
                    "milestones": [
                        {
                            "id": str(milestone.id),
                            "title": milestone.title,
                            "subtitle": milestone.team.name,
                            "href": f"/teams/{milestone.team_id}/milestones?milestone={milestone.id}",
                            "type": "milestone",
                            "status": milestone.status,
                        }
                        for milestone in milestones
                    ],
                },
                "counts": {
                    "tasks": len(tasks),
                    "teams": len(teams),
                    "comments": len(comments),
                    "people": len(people),
                    "announcements": len(announcements),
                    "milestones": len(milestones),
                },
            },
        )
