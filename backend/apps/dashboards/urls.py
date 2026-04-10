from django.urls import path

from apps.dashboards.views import (
    AdminDashboardOverviewView,
    PersonalDashboardCalendarView,
    PersonalDashboardCompletedThisWeekView,
    PersonalDashboardOverdueView,
    PersonalDashboardSummaryView,
    PersonalDashboardTasksView,
    TeamDashboardActivityView,
    TeamDashboardCalendarView,
    TeamMemberOverviewView,
    TeamDashboardPriorityDistributionView,
    TeamDashboardProgressView,
    TeamDashboardStatusDistributionView,
    TeamDashboardSummaryView,
    TeamDashboardWorkloadView,
)

app_name = "dashboards"

urlpatterns = [
    path("admin/overview/", AdminDashboardOverviewView.as_view(), name="admin-overview"),
    path("me/summary/", PersonalDashboardSummaryView.as_view(), name="me-summary"),
    path("me/tasks/", PersonalDashboardTasksView.as_view(), name="me-tasks"),
    path("me/overdue/", PersonalDashboardOverdueView.as_view(), name="me-overdue"),
    path(
        "me/completed-this-week/",
        PersonalDashboardCompletedThisWeekView.as_view(),
        name="me-completed-this-week",
    ),
    path("me/calendar/", PersonalDashboardCalendarView.as_view(), name="me-calendar"),
    path("teams/<uuid:team_id>/summary/", TeamDashboardSummaryView.as_view(), name="team-summary"),
    path("teams/<uuid:team_id>/member-overview/", TeamMemberOverviewView.as_view(), name="team-member-overview"),
    path("teams/<uuid:team_id>/activity/", TeamDashboardActivityView.as_view(), name="team-activity"),
    path("teams/<uuid:team_id>/progress/", TeamDashboardProgressView.as_view(), name="team-progress"),
    path("teams/<uuid:team_id>/calendar/", TeamDashboardCalendarView.as_view(), name="team-calendar"),
    path("teams/<uuid:team_id>/workload/", TeamDashboardWorkloadView.as_view(), name="team-workload"),
    path(
        "teams/<uuid:team_id>/status-distribution/",
        TeamDashboardStatusDistributionView.as_view(),
        name="team-status-distribution",
    ),
    path(
        "teams/<uuid:team_id>/priority-distribution/",
        TeamDashboardPriorityDistributionView.as_view(),
        name="team-priority-distribution",
    ),
]
