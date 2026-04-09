from __future__ import annotations

import os
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.attachments.storage import (
    LocalAttachmentStorageProvider,
    SupabaseAttachmentStorageProvider,
    SupabaseS3AttachmentStorageProvider,
)
from apps.attachments.tests.utils import TemporaryMediaRootMixin


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
            provider.client,
            "create_signed_url",
            return_value="https://example.supabase.co/storage/v1/object/sign/attachments/tasks/file.pdf?token=test&download=file.pdf",
        ):
            url = provider.generate_download_url(
                file_path="tasks/file.pdf",
                expires_in=300,
                download_filename="file.pdf",
            )

        self.assertIn("token=test", url)
        self.assertIn("download=file.pdf", url)


@override_settings(
    SUPABASE_S3_ENDPOINT="https://project.storage.supabase.co/storage/v1/s3",
    SUPABASE_S3_REGION="eu-west-1",
    SUPABASE_S3_ACCESS_KEY_ID="access-key",
    SUPABASE_S3_SECRET_ACCESS_KEY="secret-key",
    SUPABASE_S3_BUCKET="attachments",
    SUPABASE_S3_FORCE_PATH_STYLE=True,
)
class SupabaseS3AttachmentStorageProviderTests(TestCase):
    def test_generate_download_url_includes_signed_s3_parameters(self) -> None:
        provider = SupabaseS3AttachmentStorageProvider()

        url = provider.generate_download_url(
            file_path="tasks/file.pdf",
            expires_in=300,
            download_filename="file.pdf",
        )

        self.assertIn("X-Amz-Algorithm=AWS4-HMAC-SHA256", url)
        self.assertIn("/storage/v1/s3/attachments/tasks/file.pdf", url)
        self.assertIn("response-content-disposition=attachment", url)
