from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

from django.conf import settings
from django.utils.text import get_valid_filename
from rest_framework.serializers import ValidationError

from apps.attachments.constants import (
    DEFAULT_ALLOWED_ATTACHMENT_TYPES,
    GENERIC_BINARY_MIME_TYPES,
    INLINE_PREVIEW_MIME_PREFIXES,
    INLINE_PREVIEW_MIME_TYPES,
)


def _format_bytes(size: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    size_value = float(size)
    for unit in units:
        if size_value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(size_value)} {unit}"
            return f"{size_value:.1f} {unit}"
        size_value /= 1024
    return f"{size} B"


def sanitize_attachment_name(filename: str) -> str:
    raw_name = Path(filename or "").name.strip()
    if not raw_name:
        raise ValidationError({"file": ["A file name is required."]})

    suffix = Path(raw_name).suffix.lower()
    stem = get_valid_filename(Path(raw_name).stem) or "attachment"
    max_stem_length = 255 - len(suffix)
    stem = stem[:max_stem_length] or "attachment"
    return f"{stem}{suffix}"


def build_safe_internal_filename(original_name: str) -> str:
    return f"{uuid.uuid4().hex}{Path(original_name).suffix.lower()}"


def is_previewable_mime_type(mime_type: str) -> bool:
    return mime_type in INLINE_PREVIEW_MIME_TYPES or mime_type.startswith(INLINE_PREVIEW_MIME_PREFIXES)


def validate_attachment_upload(uploaded_file) -> dict[str, str | int]:
    if uploaded_file is None:
        raise ValidationError({"file": ["A file must be provided."]})

    if uploaded_file.size <= 0:
        raise ValidationError({"file": ["Empty files cannot be uploaded."]})

    max_file_size = getattr(settings, "ATTACHMENTS_MAX_FILE_SIZE", 10 * 1024 * 1024)
    if uploaded_file.size > max_file_size:
        raise ValidationError(
            {
                "file": [
                    f"File size exceeds the allowed limit of {_format_bytes(max_file_size)}.",
                ]
            }
        )

    original_name = sanitize_attachment_name(uploaded_file.name)
    extension = Path(original_name).suffix.lower()
    if not extension or extension not in DEFAULT_ALLOWED_ATTACHMENT_TYPES:
        allowed_extensions = ", ".join(sorted(DEFAULT_ALLOWED_ATTACHMENT_TYPES))
        raise ValidationError({"file": [f"Unsupported file type. Allowed types: {allowed_extensions}."]})

    provided_mime_type = (getattr(uploaded_file, "content_type", "") or "").lower().strip()
    guessed_mime_type = (mimetypes.guess_type(original_name)[0] or "").lower()
    resolved_mime_type = provided_mime_type or guessed_mime_type
    allowed_mime_types = DEFAULT_ALLOWED_ATTACHMENT_TYPES[extension]

    if resolved_mime_type and resolved_mime_type not in allowed_mime_types and resolved_mime_type not in GENERIC_BINARY_MIME_TYPES:
        raise ValidationError({"file": ["The uploaded file MIME type does not match the allowed file type."]})

    if not resolved_mime_type:
        resolved_mime_type = next(iter(allowed_mime_types))

    return {
        "original_name": original_name,
        "mime_type": resolved_mime_type,
        "file_size": uploaded_file.size,
    }
