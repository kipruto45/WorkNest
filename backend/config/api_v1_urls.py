import json
from pathlib import Path

from django.http import HttpResponse
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.views import SpectacularAPIView

from apps.comments.views import CommentListCreateView
from apps.common.views import APIRootView


def render_swagger_ui(_request):
    return HttpResponse(
        """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>WorkNest API Docs</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
    <style>
      body { margin: 0; background: #f8fafc; }
      .topbar { display: none; }
    </style>
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      window.ui = SwaggerUIBundle({
        url: "/api/v1/schema/",
        dom_id: "#swagger-ui",
        deepLinking: true,
        presets: [SwaggerUIBundle.presets.apis]
      });
    </script>
  </body>
</html>
        """.strip(),
        content_type="text/html; charset=utf-8",
    )


def render_redoc_ui(_request):
    return HttpResponse(
        """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>WorkNest API Reference</title>
    <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"></script>
    <style>
      body { margin: 0; background: #fff; }
    </style>
  </head>
  <body>
    <redoc spec-url="/api/v1/schema/"></redoc>
  </body>
</html>
        """.strip(),
        content_type="text/html; charset=utf-8",
    )


def _fallback_schema(request):
    backend_url = request.build_absolute_uri("/").rstrip("/")
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "WorkNest API",
            "version": "1.0.0",
            "description": "Fallback OpenAPI schema for the deployed backend.",
        },
        "servers": [{"url": backend_url}],
        "paths": {
            "/api/v1/": {
                "get": {
                    "summary": "API root",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/v1/health/live/": {
                "get": {
                    "summary": "Liveness probe",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/v1/health/ready/": {
                "get": {
                    "summary": "Readiness probe",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/v1/system/info/": {
                "get": {
                    "summary": "System info",
                    "responses": {"200": {"description": "OK"}},
                }
            },
            "/api/v1/auth/me/": {
                "get": {
                    "summary": "Current user",
                    "responses": {"200": {"description": "OK"}},
                }
            },
        },
    }


@csrf_exempt
def serve_schema(request):
    schema_path = Path(__file__).resolve().parents[1] / "schema" / "openapi.json"
    if schema_path.exists():
        try:
            return HttpResponse(schema_path.read_text(), content_type="application/vnd.oai.openapi+json")
        except Exception:
            pass

    try:
        return SpectacularAPIView.as_view()(request)
    except Exception:
        return HttpResponse(
            json.dumps(_fallback_schema(request)),
            content_type="application/vnd.oai.openapi+json",
        )

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
    path("schema/", serve_schema, name="schema"),
    path("docs/", render_swagger_ui, name="docs"),
    path("docs/swagger/", render_swagger_ui, name="swagger-ui"),
    path("docs/redoc/", render_redoc_ui, name="redoc"),
]
