from __future__ import annotations

import os
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.attachments.tests.utils import TemporaryMediaRootMixin
from apps.integrations.storage.local import LocalStorageProvider
from apps.integrations.storage.services import generate_private_file_url, get_storage_provider, using_supabase_s3_storage
from apps.integrations.storage.supabase_s3 import SupabaseS3StorageProvider


class LocalStorageProviderTests(TemporaryMediaRootMixin, TestCase):
    def test_local_storage_provider_can_upload_and_open_file(self) -> None:
        provider = LocalStorageProvider()
        stored = provider.upload_file(
            file_obj=SimpleUploadedFile("demo.txt", b"hello", content_type="text/plain"),
            destination_path="tasks/demo/demo.txt",
            mime_type="text/plain",
        )

        with provider.open_file(file_path=stored.file_path) as handle:
            self.assertEqual(handle.read(), b"hello")

        provider.delete_file(file_path=stored.file_path)
        self.assertFalse(os.path.exists(os.path.join(self._temp_media_root, stored.file_path)))


@override_settings(
    ATTACHMENTS_STORAGE_BACKEND="supabase",
    SUPABASE_URL="https://example.supabase.co",
    SUPABASE_KEY="service-key",
    ATTACHMENTS_SUPABASE_BUCKET="attachments",
)
class SupabaseStorageServiceTests(TestCase):
    def test_generate_private_file_url_uses_provider_response(self) -> None:
        mocked_provider = Mock()
        mocked_provider.generate_download_url.return_value = "https://example.com/signed"

        with patch("apps.integrations.storage.services.get_storage_provider", return_value=mocked_provider):
            url = generate_private_file_url(
                file_path="tasks/demo/file.pdf",
                expires_in=300,
                provider_name="supabase",
                download_filename="file.pdf",
            )

        self.assertEqual(url, "https://example.com/signed")


@override_settings(
    ATTACHMENTS_STORAGE_BACKEND="supabase_s3",
    SUPABASE_S3_ENDPOINT="https://project.storage.supabase.co/storage/v1/s3",
    SUPABASE_S3_REGION="eu-west-1",
    SUPABASE_S3_ACCESS_KEY_ID="access-key",
    SUPABASE_S3_SECRET_ACCESS_KEY="secret-key",
    SUPABASE_S3_BUCKET="attachments",
    SUPABASE_S3_FORCE_PATH_STYLE=True,
)
class SupabaseS3StorageServiceTests(TestCase):
    def test_storage_provider_switches_to_supabase_s3(self) -> None:
        provider = get_storage_provider()

        self.assertIsInstance(provider, SupabaseS3StorageProvider)
        self.assertTrue(using_supabase_s3_storage())
