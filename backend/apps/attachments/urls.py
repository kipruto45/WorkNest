from django.urls import path

from apps.attachments.views import (
    AttachmentDetailView,
    AttachmentDownloadView,
    AttachmentPreviewView,
    TaskAttachmentListCreateView,
)

app_name = "attachments"

urlpatterns = [
    path("tasks/<uuid:task_id>/attachments/", TaskAttachmentListCreateView.as_view(), name="task-list-create"),
    path("attachments/<uuid:pk>/", AttachmentDetailView.as_view(), name="detail"),
    path("attachments/<uuid:pk>/download/", AttachmentDownloadView.as_view(), name="download"),
    path("attachments/<uuid:pk>/preview/", AttachmentPreviewView.as_view(), name="preview"),
]
