from __future__ import annotations

import json
import os
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.attachments.storage import LocalAttachmentStorageProvider, SupabaseAttachmentStorageProvider
from apps.attachments.tests.utils import TemporaryMediaRootMixin


class DummyResponse:
    def __init__(self, payload: dict[str, str]) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class LocalAttachmentStorageProviderTests(TemporaryMediaRootMixin, TestCase):
    def test_local_provider_can_upload_open_and_delete_file(self) -> None:
        provider = LocalAttachmentStorageProvider()
        stored = provider.upload_file(
            file_obj=SimpleUploadedFile("brief.txt", b"hello", content_type="text/plain"),
            destination_path="tasks/test/brief.txt",
            mime_type="text/plain",
        )

        with provider.open_file(file_path=stored.file_path) as handle:
            self.assertEqual(handle.read(), b"hello")

        provider.delete_file(file_path=stored.file_path)

        self.assertFalse(os.path.exists(os.path.join(self._temp_media_root, stored.file_path)))


@override_settings(
    SUPABASE_URL="https://example.supabase.co",
    SUPABASE_KEY="service-key",
    ATTACHMENTS_SUPABASE_BUCKET="attachments",
)
class SupabaseAttachmentStorageProviderTests(TestCase):
    def test_generate_download_url_uses_signed_url_response(self) -> None:
        provider = SupabaseAttachmentStorageProvider()

        with patch.object(
            provider,
            "_request",
            return_value=DummyResponse({"signedURL": "/storage/v1/object/sign/attachments/tasks/file.pdf?token=test"}),
        ):
            url = provider.generate_download_url(
                file_path="tasks/file.pdf",
                expires_in=300,
                download_filename="file.pdf",
            )

        self.assertIn("token=test", url)
        self.assertIn("download=file.pdf", url)
