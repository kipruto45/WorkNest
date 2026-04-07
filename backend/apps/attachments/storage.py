from __future__ import annotations

import json

from django.conf import settings

from apps.integrations.exceptions import StorageProviderError as AttachmentStorageError
from apps.integrations.storage.base import BaseStorageProvider as BaseAttachmentStorageProvider
from apps.integrations.storage.base import StoredFile as StoredAttachment
from apps.integrations.storage.local import LocalStorageProvider
from apps.integrations.storage.services import get_storage_provider
from apps.integrations.storage.supabase import SupabaseStorageProvider
from apps.integrations.supabase.utils import build_storage_sign_url, normalize_signed_url


class LocalAttachmentStorageProvider(LocalStorageProvider):
    pass


class SupabaseAttachmentStorageProvider(SupabaseStorageProvider):
    def _request(self, *, method: str, url: str, data: bytes | None = None, headers: dict[str, str] | None = None):
        return self.client.client.request(method=method, url=url, data=data, headers=headers)

    def generate_download_url(self, *, file_path: str, expires_in: int, download_filename: str | None = None) -> str:
        sign_url = build_storage_sign_url(
            base_url=getattr(settings, "SUPABASE_URL", ""),
            bucket=self.bucket,
            file_path=file_path,
        )
        payload = json.dumps({"expiresIn": expires_in}).encode("utf-8")
        with self._request(method="POST", url=sign_url, data=payload, headers={"Content-Type": "application/json"}) as response:
            response_payload = json.loads(response.read().decode("utf-8"))

        signed_url = response_payload.get("signedURL") or response_payload.get("signedUrl")
        if not signed_url:
            raise AttachmentStorageError("Supabase did not return a signed attachment URL.")
        return normalize_signed_url(
            base_url=getattr(settings, "SUPABASE_URL", ""),
            signed_url=signed_url,
            download_filename=download_filename,
        )


def get_attachment_storage_provider(provider_name: str | None = None) -> BaseAttachmentStorageProvider:
    storage_provider = get_storage_provider(provider_name=provider_name)
    if storage_provider.provider_name == LocalAttachmentStorageProvider.provider_name:
        return LocalAttachmentStorageProvider()
    return SupabaseAttachmentStorageProvider()
