from __future__ import annotations

from django.http import FileResponse, HttpResponseRedirect
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.views import APIView

from apps.attachments.permissions import CanDeleteAttachment, CanUploadAttachment, CanViewAttachment
from apps.attachments.selectors import get_attachment_for_user, get_task_for_attachment_access
from apps.attachments.serializers import AttachmentDetailSerializer, AttachmentListSerializer, AttachmentUploadSerializer
from apps.attachments.services import delete_attachment, get_attachment_download, list_task_attachments, upload_attachment
from apps.attachments.storage import AttachmentStorageError
from apps.common.api.mixins import PermissionEnforcerMixin
from apps.common.responses import error_response, success_response


class TaskAttachmentListCreateView(PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses=AttachmentListSerializer(many=True))
    def get(self, request, task_id, *args, **kwargs):  # type: ignore[override]
        task = get_task_for_attachment_access(task_id=task_id, user=request.user, include_archived=True)
        if not task:
            return success_response(
                request=request,
                message="Task not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self.enforce_permission(request=request, permission_class=CanViewAttachment, obj=task)
        attachments = list_task_attachments(task=task, user=request.user)
        serializer = AttachmentListSerializer(attachments, many=True, context={"request": request})
        return success_response(
            request=request,
            message="Attachments retrieved successfully.",
            data=serializer.data,
        )

    @extend_schema(request=AttachmentUploadSerializer, responses=AttachmentDetailSerializer)
    def post(self, request, task_id, *args, **kwargs):  # type: ignore[override]
        task = get_task_for_attachment_access(task_id=task_id, user=request.user, include_archived=True)
        if not task:
            return success_response(
                request=request,
                message="Task not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self.enforce_permission(request=request, permission_class=CanUploadAttachment, obj=task)
        serializer = AttachmentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attachment = upload_attachment(task=task, uploaded_by=request.user, file_obj=serializer.validated_data["file"])
        return success_response(
            request=request,
            message="Attachment uploaded successfully.",
            data=AttachmentDetailSerializer(attachment, context={"request": request}).data,
            status_code=status.HTTP_201_CREATED,
        )


class AttachmentDetailView(PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_attachment(self, pk, user):
        return get_attachment_for_user(attachment_id=pk, user=user, include_deleted=False)

    @extend_schema(responses=AttachmentDetailSerializer)
    def get(self, request, pk, *args, **kwargs):  # type: ignore[override]
        attachment = self.get_attachment(pk, request.user)
        if not attachment:
            return success_response(
                request=request,
                message="Attachment not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self.enforce_permission(request=request, permission_class=CanViewAttachment, obj=attachment)
        return success_response(
            request=request,
            message="Attachment retrieved successfully.",
            data=AttachmentDetailSerializer(attachment, context={"request": request}).data,
        )

    def delete(self, request, pk, *args, **kwargs):  # type: ignore[override]
        attachment = self.get_attachment(pk, request.user)
        if not attachment:
            return success_response(
                request=request,
                message="Attachment not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self.enforce_permission(request=request, permission_class=CanDeleteAttachment, obj=attachment)
        delete_attachment(attachment=attachment, deleted_by=request.user)
        return success_response(
            request=request,
            message="Attachment deleted successfully.",
            data=None,
            status_code=status.HTTP_204_NO_CONTENT,
        )


class AttachmentDownloadView(PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):  # type: ignore[override]
        attachment = get_attachment_for_user(attachment_id=pk, user=request.user, include_deleted=False)
        if not attachment:
            return success_response(
                request=request,
                message="Attachment not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self.enforce_permission(request=request, permission_class=CanViewAttachment, obj=attachment)
        try:
            download_result = get_attachment_download(attachment=attachment, as_attachment=True)
        except AttachmentStorageError as exc:
            return error_response(
                request=request,
                message="Attachment download is currently unavailable.",
                errors={"detail": [str(exc)]},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if download_result.redirect_url:
            response = HttpResponseRedirect(download_result.redirect_url)
        else:
            response = FileResponse(
                download_result.file_handle,
                as_attachment=download_result.as_attachment,
                filename=download_result.file_name,
                content_type=download_result.mime_type,
            )
        response["X-Content-Type-Options"] = "nosniff"
        return response


class AttachmentPreviewView(PermissionEnforcerMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):  # type: ignore[override]
        attachment = get_attachment_for_user(attachment_id=pk, user=request.user, include_deleted=False)
        if not attachment:
            return success_response(
                request=request,
                message="Attachment not found.",
                data=None,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        self.enforce_permission(request=request, permission_class=CanViewAttachment, obj=attachment)
        try:
            download_result = get_attachment_download(attachment=attachment, as_attachment=False)
        except AttachmentStorageError as exc:
            return error_response(
                request=request,
                message="Attachment preview is currently unavailable.",
                errors={"detail": [str(exc)]},
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if download_result.redirect_url:
            response = HttpResponseRedirect(download_result.redirect_url)
        else:
            response = FileResponse(
                download_result.file_handle,
                as_attachment=False,
                filename=download_result.file_name,
                content_type=download_result.mime_type,
            )
        response["X-Content-Type-Options"] = "nosniff"
        return response
