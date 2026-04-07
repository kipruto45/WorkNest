from __future__ import annotations

from django.conf import settings

from apps.integrations.constants import STORAGE_PROVIDER_SUPABASE
from apps.integrations.exceptions import (
    IntegrationConfigurationError,
    StorageDeleteFailedError,
    StorageDownloadUrlError,
    StorageProviderError,
    StorageUploadFailedError,
)
from apps.integrations.storage.base import BaseStorageProvider, StoredFile
from apps.integrations.supabase.storage import SupabaseStorageClient
from apps.integrations.validators import sanitize_provider_error, validate_storage_path


class SupabaseStorageProvider(BaseStorageProvider):
    provider_name = STORAGE_PROVIDER_SUPABASE

    def __init__(self, *, bucket: str | None = None, client: SupabaseStorageClient | None = None) -> None:
        self.bucket = bucket or getattr(settings, "ATTACHMENTS_SUPABASE_BUCKET", "")
        if not self.bucket:
            raise IntegrationConfigurationError("Supabase storage requires ATTACHMENTS_SUPABASE_BUCKET.")
        self.client = client or SupabaseStorageClient()

    def upload_file(self, *, file_obj, destination_path: str, mime_type: str) -> StoredFile:
        safe_path = validate_storage_path(destination_path)
        try:
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            payload = file_obj.read()
            self.client.upload_object(
                bucket=self.bucket,
                file_path=safe_path,
                payload=payload,
                content_type=mime_type,
            )
        except Exception as exc:
            raise StorageUploadFailedError(
                sanitize_provider_error(exc, fallback_message="Supabase upload failed.")
            ) from exc
        return StoredFile(file_path=safe_path, storage_provider=self.provider_name)

    def delete_file(self, *, file_path: str) -> None:
        safe_path = validate_storage_path(file_path)
        try:
            self.client.delete_object(bucket=self.bucket, file_path=safe_path)
        except Exception as exc:
            raise StorageDeleteFailedError(
                sanitize_provider_error(exc, fallback_message="Supabase delete failed.")
            ) from exc

    def open_file(self, *, file_path: str):
        raise StorageProviderError("Supabase files are served through signed URLs, not direct streaming.")

    def generate_download_url(self, *, file_path: str, expires_in: int, download_filename: str | None = None) -> str:
        safe_path = validate_storage_path(file_path)
        try:
            return self.client.create_signed_url(
                bucket=self.bucket,
                file_path=safe_path,
                expires_in=expires_in,
                download_filename=download_filename,
            )
        except Exception as exc:
            raise StorageDownloadUrlError(
                sanitize_provider_error(exc, fallback_message="Supabase signed URL generation failed.")
            ) from exc
