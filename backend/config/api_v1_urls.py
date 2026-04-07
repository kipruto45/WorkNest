from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.comments.views import CommentListCreateView
from apps.common.views import APIRootView

urlpatterns = [
    path("", APIRootView.as_view(), name="root"),
    path("", include(("apps.common.urls", "common"), namespace="common")),
    path("", include(("apps.audit_logs.urls", "audit_logs"), namespace="audit_logs")),
    path("auth/", include(("apps.authentication.urls", "authentication"), namespace="authentication")),
    path("", include(("apps.attachments.urls", "attachments"), namespace="attachments")),
    path("dashboard/", include(("apps.dashboards.urls", "dashboards"), namespace="dashboards")),
    path("users/", include(("apps.users.urls", "users"), namespace="users")),
    path("teams/", include(("apps.teams.urls", "teams"), namespace="teams")),
    path("invitations/", include(("apps.memberships.urls", "memberships"), namespace="memberships")),
    path("tasks/<uuid:task_id>/comments/", CommentListCreateView.as_view(), name="task-comments"),
    path("tasks/", include(("apps.tasks.urls", "tasks"), namespace="tasks")),
    path("comments/", include(("apps.comments.urls", "comments"), namespace="comments")),
    path("notifications/", include(("apps.notifications.urls", "notifications"), namespace="notifications")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api_v1:schema"), name="docs"),
    path("docs/swagger/", SpectacularSwaggerView.as_view(url_name="api_v1:schema"), name="swagger-ui"),
    path("docs/redoc/", SpectacularRedocView.as_view(url_name="api_v1:schema"), name="redoc"),
]
