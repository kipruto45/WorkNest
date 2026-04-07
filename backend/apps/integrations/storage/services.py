from __future__ import annotations

from django.conf import settings

from apps.integrations.constants import DEFAULT_STORAGE_PROVIDER, STORAGE_PROVIDER_LOCAL, STORAGE_PROVIDER_SUPABASE
from apps.integrations.storage.local import LocalStorageProvider
from apps.integrations.storage.supabase import SupabaseStorageProvider
from apps.integrations.validators import validate_provider_name


def get_storage_provider(provider_name: str | None = None, *, bucket: str | None = None):
    resolved_provider = validate_provider_name(
        provider_name=provider_name or getattr(settings, "ATTACHMENTS_STORAGE_BACKEND", DEFAULT_STORAGE_PROVIDER),
        supported_providers={STORAGE_PROVIDER_LOCAL, STORAGE_PROVIDER_SUPABASE},
        provider_kind="storage",
    )
    if resolved_provider == STORAGE_PROVIDER_SUPABASE:
        return SupabaseStorageProvider(bucket=bucket)
    return LocalStorageProvider()


def upload_file_to_storage(*, file_obj, destination_path: str, mime_type: str, provider_name: str | None = None, bucket: str | None = None):
    return get_storage_provider(provider_name=provider_name, bucket=bucket).upload_file(
        file_obj=file_obj,
        destination_path=destination_path,
        mime_type=mime_type,
    )


def delete_file_from_storage(*, file_path: str, provider_name: str | None = None, bucket: str | None = None) -> None:
    return get_storage_provider(provider_name=provider_name, bucket=bucket).delete_file(file_path=file_path)


def open_storage_file(*, file_path: str, provider_name: str | None = None, bucket: str | None = None):
    return get_storage_provider(provider_name=provider_name, bucket=bucket).open_file(file_path=file_path)


def generate_private_file_url(
    *,
    file_path: str,
    expires_in: int,
    provider_name: str | None = None,
    bucket: str | None = None,
    download_filename: str | None = None,
) -> str:
    return get_storage_provider(provider_name=provider_name, bucket=bucket).generate_download_url(
        file_path=file_path,
        expires_in=expires_in,
        download_filename=download_filename,
    )
