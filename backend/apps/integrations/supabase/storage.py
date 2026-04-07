from __future__ import annotations

import json

from apps.integrations.supabase.client import SupabaseClient
from apps.integrations.supabase.utils import build_storage_object_url, build_storage_sign_url, normalize_signed_url


class SupabaseStorageClient:
    def __init__(self, *, client: SupabaseClient | None = None) -> None:
        self.client = client or SupabaseClient()

    def upload_object(self, *, bucket: str, file_path: str, payload: bytes, content_type: str) -> None:
        with self.client.request(
            method="POST",
            url=build_storage_object_url(base_url=self.client.base_url, bucket=bucket, file_path=file_path),
            data=payload,
            headers={
                "Content-Type": content_type or "application/octet-stream",
                "x-upsert": "false",
            },
        ):
            return None

    def delete_object(self, *, bucket: str, file_path: str) -> None:
        with self.client.request(
            method="DELETE",
            url=build_storage_object_url(base_url=self.client.base_url, bucket=bucket, file_path=file_path),
        ):
            return None

    def create_signed_url(self, *, bucket: str, file_path: str, expires_in: int, download_filename: str | None = None) -> str:
        payload = json.dumps({"expiresIn": expires_in}).encode("utf-8")
        with self.client.request(
            method="POST",
            url=build_storage_sign_url(base_url=self.client.base_url, bucket=bucket, file_path=file_path),
            data=payload,
            headers={"Content-Type": "application/json"},
        ) as response:
            response_payload = json.loads(response.read().decode("utf-8"))

        signed_url = response_payload.get("signedURL") or response_payload.get("signedUrl")
        if not signed_url:
            raise ValueError("Supabase did not return a signed URL.")
        return normalize_signed_url(
            base_url=self.client.base_url,
            signed_url=signed_url,
            download_filename=download_filename,
        )
