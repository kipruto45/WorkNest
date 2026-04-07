from __future__ import annotations

from django.core.files.storage import default_storage

from apps.integrations.constants import STORAGE_PROVIDER_LOCAL
from apps.integrations.exceptions import StorageProviderError, StorageUploadFailedError
from apps.integrations.storage.base import BaseStorageProvider, StoredFile
from apps.integrations.validators import sanitize_provider_error, validate_storage_path


class LocalStorageProvider(BaseStorageProvider):
    provider_name = STORAGE_PROVIDER_LOCAL

    def upload_file(self, *, file_obj, destination_path: str, mime_type: str) -> StoredFile:
        safe_path = validate_storage_path(destination_path)
        try:
            saved_path = default_storage.save(safe_path, file_obj)
        except Exception as exc:  # pragma: no cover
            raise StorageUploadFailedError(
                sanitize_provider_error(exc, fallback_message="Local storage upload failed.")
            ) from exc
        return StoredFile(file_path=saved_path, storage_provider=self.provider_name)

    def delete_file(self, *, file_path: str) -> None:
        default_storage.delete(validate_storage_path(file_path))

    def open_file(self, *, file_path: str):
        safe_path = validate_storage_path(file_path)
        try:
            return default_storage.open(safe_path, "rb")
        except FileNotFoundError as exc:
            raise StorageProviderError("The requested file could not be found.") from exc

    def generate_download_url(self, *, file_path: str, expires_in: int, download_filename: str | None = None) -> str:
        raise StorageProviderError("Local storage files are served through application download endpoints.")
