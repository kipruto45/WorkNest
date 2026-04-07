from __future__ import annotations

from django.db import models


class AttachmentStorageProvider(models.TextChoices):
    LOCAL = "local", "Local"
    SUPABASE = "supabase", "Supabase"


DEFAULT_ALLOWED_ATTACHMENT_TYPES = {
    ".pdf": {"application/pdf"},
    ".png": {"image/png"},
    ".jpg": {"image/jpeg"},
    ".jpeg": {"image/jpeg"},
    ".doc": {"application/msword"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".xls": {"application/vnd.ms-excel"},
    ".xlsx": {"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"},
    ".txt": {"text/plain"},
    ".zip": {"application/zip", "application/x-zip-compressed", "multipart/x-zip"},
}

GENERIC_BINARY_MIME_TYPES = {
    "application/octet-stream",
    "binary/octet-stream",
}

INLINE_PREVIEW_MIME_TYPES = {
    "application/pdf",
    "text/plain",
}

INLINE_PREVIEW_MIME_PREFIXES = (
    "image/",
)
