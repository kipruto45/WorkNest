from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from apps.audit_logs.constants import AuditAction
from apps.audit_logs.services import build_audit_metadata, log_attachment_action
from rest_framework.serializers import ValidationError

from apps.attachments.constants import AttachmentStorageProvider
from apps.attachments.models import Attachment
from apps.attachments.selectors import get_task_attachments
from apps.attachments.storage import get_attachment_storage_provider
from apps.attachments.validators import (
    build_safe_internal_filename,
    is_previewable_mime_type,
    validate_attachment_upload,
)


@dataclass
class AttachmentDownloadResult:
    redirect_url: str | None = None
    file_handle: object | None = None
    file_name: str = ""
    mime_type: str = ""
    as_attachment: bool = True


def build_attachment_storage_path(*, task, original_name: str) -> tuple[str, str]:
    internal_name = build_safe_internal_filename(original_name)
    today = date.today()
    storage_path = Path("tasks") / str(task.id) / f"{today:%Y}" / f"{today:%m}" / internal_name
    return storage_path.as_posix(), internal_name


def store_attachment_metadata(
    *,
    task,
    uploaded_by,
    original_name: str,
    file_name: str,
    file_path: str,
    file_size: int,
    mime_type: str,
    storage_provider: str,
) -> Attachment:
    attachment = Attachment.objects.create(
        task=task,
        uploaded_by=uploaded_by,
        original_name=original_name,
        file_name=file_name,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        storage_provider=storage_provider,
    )
    attachment.file_url = reverse("api_v1:attachments:download", kwargs={"pk": attachment.pk})
    attachment.save(update_fields=["file_url", "updated_at"])
    return attachment


def emit_attachment_uploaded_event(*, attachment: Attachment) -> None:
    # This hook keeps the module ready for future notifications or audit logging.
    log_attachment_action(
        actor=attachment.uploaded_by,
        action=AuditAction.ATTACHMENT_UPLOADED,
        attachment=attachment,
        metadata=build_audit_metadata(
            original_name=attachment.original_name,
            file_size=attachment.file_size,
            mime_type=attachment.mime_type,
            storage_provider=attachment.storage_provider,
        ),
    )
    from apps.integrations.email.services import queue_attachment_uploaded_email

    recipients = []
    for user in [attachment.task.assigned_to, attachment.task.created_by]:
        if user is None:
            continue
        if attachment.uploaded_by_id and user.id == attachment.uploaded_by_id:
            continue
        if any(existing.id == user.id for existing in recipients):
            continue
        recipients.append(user)

    for recipient in recipients:
        transaction.on_commit(lambda recipient=recipient: queue_attachment_uploaded_email(attachment=attachment, recipient=recipient))
    return None


def emit_attachment_deleted_event(*, attachment: Attachment, deleted_by) -> None:
    # This hook keeps the module ready for future notifications or audit logging.
    log_attachment_action(
        actor=deleted_by,
        action=AuditAction.ATTACHMENT_DELETED,
        attachment=attachment,
        metadata=build_audit_metadata(
            original_name=attachment.original_name,
            file_size=attachment.file_size,
            mime_type=attachment.mime_type,
            storage_provider=attachment.storage_provider,
        ),
    )
    return None


def upload_attachment(*, task, uploaded_by, file_obj) -> Attachment:
    metadata = validate_attachment_upload(file_obj)
    storage_provider = get_attachment_storage_provider()
    file_path, file_name = build_attachment_storage_path(task=task, original_name=metadata["original_name"])
    stored_file = storage_provider.upload_file(
        file_obj=file_obj,
        destination_path=file_path,
        mime_type=str(metadata["mime_type"]),
    )

    try:
        attachment = store_attachment_metadata(
            task=task,
            uploaded_by=uploaded_by,
            original_name=str(metadata["original_name"]),
            file_name=file_name,
            file_path=stored_file.file_path,
            file_size=int(metadata["file_size"]),
            mime_type=str(metadata["mime_type"]),
            storage_provider=stored_file.storage_provider,
        )
    except Exception:
        storage_provider.delete_file(file_path=stored_file.file_path)
        raise

    emit_attachment_uploaded_event(attachment=attachment)
    return attachment


def remove_attachment_from_storage(*, attachment: Attachment) -> None:
    storage_provider = get_attachment_storage_provider(attachment.storage_provider)
    storage_provider.delete_file(file_path=attachment.file_path)


def delete_attachment(*, attachment: Attachment, deleted_by) -> Attachment:
    remove_attachment_from_storage(attachment=attachment)
    attachment.soft_delete()
    attachment.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
    emit_attachment_deleted_event(attachment=attachment, deleted_by=deleted_by)
    return attachment


def list_task_attachments(*, task, user):
    return get_task_attachments(task=task, user=user)


def get_attachment_download_url(*, attachment: Attachment, expires_in: int | None = None, as_attachment: bool = True) -> str:
    if attachment.storage_provider == AttachmentStorageProvider.LOCAL:
        return attachment.file_url

    storage_provider = get_attachment_storage_provider(attachment.storage_provider)
    return storage_provider.generate_download_url(
        file_path=attachment.file_path,
        expires_in=expires_in or getattr(settings, "ATTACHMENTS_SIGNED_URL_TTL", 300),
        download_filename=attachment.original_name if as_attachment else None,
    )


def get_attachment_download(*, attachment: Attachment, as_attachment: bool = True) -> AttachmentDownloadResult:
    if not as_attachment and not is_previewable_mime_type(attachment.mime_type):
        raise ValidationError({"attachment": ["This attachment type cannot be previewed inline."]})

    storage_provider = get_attachment_storage_provider(attachment.storage_provider)
    if attachment.storage_provider == AttachmentStorageProvider.LOCAL:
        file_handle = storage_provider.open_file(file_path=attachment.file_path)
        return AttachmentDownloadResult(
            file_handle=file_handle,
            file_name=attachment.original_name,
            mime_type=attachment.mime_type,
            as_attachment=as_attachment,
        )

    return AttachmentDownloadResult(
        redirect_url=storage_provider.generate_download_url(
            file_path=attachment.file_path,
            expires_in=getattr(settings, "ATTACHMENTS_SIGNED_URL_TTL", 300),
            download_filename=attachment.original_name if as_attachment else None,
        ),
        file_name=attachment.original_name,
        mime_type=attachment.mime_type,
        as_attachment=as_attachment,
    )
