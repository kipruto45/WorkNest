from __future__ import annotations

from django.utils import timezone
from rest_framework import permissions
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from apps.common.api.mixins import PaginatedAPIViewMixin
from apps.common.responses import success_response
from apps.dashboards.permissions import CanViewTeamDashboard, IsPlatformAdmin
from apps.dashboards.selectors import (
    get_dashboard_team,
    get_user_assigned_tasks,
    get_user_completed_tasks_this_week,
    get_user_overdue_tasks,
    get_user_recent_activity,
)
from apps.dashboards.serializers import (
    AdminDashboardSerializer,
    DashboardCalendarEventSerializer,
    DashboardCalendarQuerySerializer,
    DashboardTaskListQuerySerializer,
    MemberActivitySerializer,
    PersonalDashboardSummarySerializer,
    PriorityDistributionItemSerializer,
    StatusDistributionItemSerializer,
    TeamDashboardSummarySerializer,
    WorkloadDistributionSerializer,
)
from apps.dashboards.services import (
    build_deadline_calendar_feed,
    build_admin_dashboard_snapshot,
    build_member_activity_metrics,
    build_personal_dashboard_summary,
    build_priority_distribution,
    build_status_distribution,
    build_team_dashboard_summary,
    build_team_progress_metrics,
    build_workload_distribution,
)
from apps.notifications.serializers import NotificationListSerializer
from apps.tasks.selectors import filter_tasks
from apps.tasks.serializers import TaskListSerializer


class TeamDashboardAccessMixin:
    permission_classes = [permissions.IsAuthenticated, CanViewTeamDashboard]

    def get_team(self, request, team_id):
        team = get_dashboard_team(team_id=team_id)
        if not team:
            raise NotFound("Team not found.")
        self.check_object_permissions(request, team)
        return team


class AdminDashboardAccessMixin:
    permission_classes = [permissions.IsAuthenticated, IsPlatformAdmin]


class PersonalDashboardSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        data = build_personal_dashboard_summary(user=request.user, reference_time=timezone.now())
        data["recent_activity"] = NotificationListSerializer(
            get_user_recent_activity(request.user),
            many=True,
        ).data
        serializer = PersonalDashboardSummarySerializer(data)
        return success_response(
            request=request,
            message="Personal dashboard summary retrieved successfully.",
            data=serializer.data,
        )


class PersonalDashboardTasksView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        query_serializer = DashboardTaskListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        queryset = filter_tasks(get_user_assigned_tasks(request.user), query_serializer.validated_data)
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=TaskListSerializer,
            message="Personal dashboard tasks retrieved successfully.",
        )


class PersonalDashboardOverdueView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        query_serializer = DashboardTaskListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        queryset = filter_tasks(get_user_overdue_tasks(request.user), query_serializer.validated_data)
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=TaskListSerializer,
            message="Personal overdue dashboard tasks retrieved successfully.",
        )


class PersonalDashboardCompletedThisWeekView(PaginatedAPIViewMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        query_serializer = DashboardTaskListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        queryset = filter_tasks(
            get_user_completed_tasks_this_week(request.user, reference_time=timezone.now()),
            query_serializer.validated_data,
        )
        return self.paginate_success_response(
            request=request,
            queryset=queryset,
            serializer_class=TaskListSerializer,
            message="Tasks completed this week retrieved successfully.",
        )


class PersonalDashboardCalendarView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):  # type: ignore[override]
        query_serializer = DashboardCalendarQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        queryset = build_deadline_calendar_feed(
            user=request.user,
            team_id=query_serializer.validated_data.get("team"),
            start=query_serializer.validated_data.get("start"),
            end=query_serializer.validated_data.get("end"),
            status=query_serializer.validated_data.get("status"),
            priority=query_serializer.validated_data.get("priority"),
        )
        serializer = DashboardCalendarEventSerializer(queryset, many=True)
        return success_response(
            request=request,
            message="Personal dashboard calendar retrieved successfully.",
            data=serializer.data,
        )


class TeamDashboardSummaryView(TeamDashboardAccessMixin, APIView):
    def get(self, request, team_id, *args, **kwargs):  # type: ignore[override]
        team = self.get_team(request, team_id)
        serializer = TeamDashboardSummarySerializer(build_team_dashboard_summary(team=team, reference_time=timezone.now()))
        return success_response(
            request=request,
            message="Team dashboard summary retrieved successfully.",
            data=serializer.data,
        )


class TeamDashboardActivityView(TeamDashboardAccessMixin, APIView):
    def get(self, request, team_id, *args, **kwargs):  # type: ignore[override]
        team = self.get_team(request, team_id)
        data = build_member_activity_metrics(team=team, reference_time=timezone.now())
        serializer = MemberActivitySerializer(data, many=True)
        return success_response(
            request=request,
            message="Team member activity retrieved successfully.",
            data={"member_activity": serializer.data},
        )


class TeamDashboardProgressView(TeamDashboardAccessMixin, APIView):
    def get(self, request, team_id, *args, **kwargs):  # type: ignore[override]
        team = self.get_team(request, team_id)
        return success_response(
            request=request,
            message="Team progress metrics retrieved successfully.",
            data=build_team_progress_metrics(team=team, reference_time=timezone.now()),
        )


class TeamDashboardCalendarView(TeamDashboardAccessMixin, APIView):
    def get(self, request, team_id, *args, **kwargs):  # type: ignore[override]
        team = self.get_team(request, team_id)
        query_serializer = DashboardCalendarQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        queryset = build_deadline_calendar_feed(
            team=team,
            start=query_serializer.validated_data.get("start"),
            end=query_serializer.validated_data.get("end"),
            assignee_id=query_serializer.validated_data.get("assignee"),
            status=query_serializer.validated_data.get("status"),
            priority=query_serializer.validated_data.get("priority"),
        )
        serializer = DashboardCalendarEventSerializer(queryset, many=True)
        return success_response(
            request=request,
            message="Team dashboard calendar retrieved successfully.",
            data=serializer.data,
        )


class TeamDashboardWorkloadView(TeamDashboardAccessMixin, APIView):
    def get(self, request, team_id, *args, **kwargs):  # type: ignore[override]
        team = self.get_team(request, team_id)
        data = build_workload_distribution(team=team, reference_time=timezone.now())
        serializer = WorkloadDistributionSerializer(data, many=True)
        return success_response(
            request=request,
            message="Team workload distribution retrieved successfully.",
            data={"workload": serializer.data},
        )


class TeamDashboardStatusDistributionView(TeamDashboardAccessMixin, APIView):
    def get(self, request, team_id, *args, **kwargs):  # type: ignore[override]
        team = self.get_team(request, team_id)
        data = build_status_distribution(team=team)
        serializer = StatusDistributionItemSerializer(data, many=True)
        return success_response(
            request=request,
            message="Team status distribution retrieved successfully.",
            data={"status_distribution": serializer.data},
        )


class TeamDashboardPriorityDistributionView(TeamDashboardAccessMixin, APIView):
    def get(self, request, team_id, *args, **kwargs):  # type: ignore[override]
        team = self.get_team(request, team_id)
        data = build_priority_distribution(team=team)
        serializer = PriorityDistributionItemSerializer(data, many=True)
        return success_response(
            request=request,
            message="Team priority distribution retrieved successfully.",
            data={"priority_distribution": serializer.data},
        )


class AdminDashboardOverviewView(AdminDashboardAccessMixin, APIView):
    def get(self, request, *args, **kwargs):  # type: ignore[override]
        serializer = AdminDashboardSerializer(build_admin_dashboard_snapshot(reference_time=timezone.now()))
        return success_response(
            request=request,
            message="Admin dashboard overview retrieved successfully.",
            data=serializer.data,
        )
