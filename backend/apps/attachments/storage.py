from __future__ import annotations

from apps.integrations.exceptions import StorageProviderError as AttachmentStorageError
from apps.integrations.storage.base import BaseStorageProvider as BaseAttachmentStorageProvider
from apps.integrations.storage.base import StoredFile as StoredAttachment
from apps.integrations.storage.local import LocalStorageProvider as LocalAttachmentStorageProvider
from apps.integrations.storage.services import get_storage_provider
from apps.integrations.storage.supabase import SupabaseStorageProvider as SupabaseAttachmentStorageProvider
from apps.integrations.storage.supabase_s3 import SupabaseS3StorageProvider as SupabaseS3AttachmentStorageProvider


def get_attachment_storage_provider(provider_name: str | None = None) -> BaseAttachmentStorageProvider:
    return get_storage_provider(provider_name=provider_name)
