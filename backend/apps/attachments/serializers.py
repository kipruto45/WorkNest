from __future__ import annotations

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import serializers

from apps.attachments.models import Attachment
from apps.attachments.permissions import CanDeleteAttachment
from apps.attachments.validators import validate_attachment_upload

User = get_user_model()


class AttachmentUploadedBySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "name", "email", "avatar")
        read_only_fields = fields


class AttachmentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate(self, attrs):
        attrs["file_metadata"] = validate_attachment_upload(attrs["file"])
        return attrs


class AttachmentListSerializer(serializers.ModelSerializer):
    task_id = serializers.UUIDField(read_only=True)
    uploaded_by = AttachmentUploadedBySerializer(read_only=True)
    file_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            "id",
            "task_id",
            "original_name",
            "file_size",
            "mime_type",
            "uploaded_by",
            "storage_provider",
            "created_at",
            "file_url",
            "preview_url",
            "can_delete",
        ]
        read_only_fields = fields

    def _build_absolute_url(self, path: str | None) -> str | None:
        if not path:
            return None

        request = self.context.get("request")
        if request is None:
            return path
        return request.build_absolute_uri(path)

    def get_file_url(self, obj: Attachment) -> str | None:
        return self._build_absolute_url(obj.file_url or reverse("api_v1:attachments:download", kwargs={"pk": obj.pk}))

    def get_preview_url(self, obj: Attachment) -> str | None:
        return self._build_absolute_url(reverse("api_v1:attachments:preview", kwargs={"pk": obj.pk}))

    def get_can_delete(self, obj: Attachment) -> bool:
        request = self.context.get("request")
        if request is None or not getattr(request, "user", None) or not request.user.is_authenticated:
            return False
        return CanDeleteAttachment().has_object_permission(request, None, obj)


class AttachmentDetailSerializer(AttachmentListSerializer):
    class Meta(AttachmentListSerializer.Meta):
        fields = AttachmentListSerializer.Meta.fields + [
            "updated_at",
        ]
