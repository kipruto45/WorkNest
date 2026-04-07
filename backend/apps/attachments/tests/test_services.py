from __future__ import annotations

import os
from unittest.mock import Mock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.attachments.models import Attachment
from apps.attachments.services import delete_attachment, get_attachment_download, upload_attachment
from apps.attachments.tests.utils import AttachmentFixtureMixin, TemporaryMediaRootMixin


class AttachmentServiceTests(TemporaryMediaRootMixin, AttachmentFixtureMixin, TestCase):
    def test_upload_attachment_persists_metadata_and_file(self) -> None:
        attachment = upload_attachment(
            task=self.task,
            uploaded_by=self.owner,
            file_obj=SimpleUploadedFile(
                "requirements.pdf",
                b"%PDF-1.4 service upload",
                content_type="application/pdf",
            ),
        )

        self.assertEqual(attachment.original_name, "requirements.pdf")
        self.assertTrue(attachment.file_path.endswith(".pdf"))
        self.assertEqual(Attachment.objects.active().count(), 1)

    def test_delete_attachment_soft_deletes_and_removes_storage_object(self) -> None:
        attachment = upload_attachment(
            task=self.task,
            uploaded_by=self.owner,
            file_obj=SimpleUploadedFile(
                "to-delete.pdf",
                b"%PDF-1.4 delete me",
                content_type="application/pdf",
            ),
        )
        stored_path = attachment.file_path

        delete_attachment(attachment=attachment, deleted_by=self.owner)
        attachment.refresh_from_db()

        self.assertTrue(attachment.is_deleted)
        self.assertFalse(Attachment.objects.active().filter(pk=attachment.pk).exists())
        self.assertFalse(os.path.exists(os.path.join(self._temp_media_root, stored_path)))

    def test_get_attachment_download_returns_redirect_for_remote_provider(self) -> None:
        attachment = Attachment.objects.create(
            task=self.task,
            uploaded_by=self.owner,
            original_name="remote.pdf",
            file_name="remote-safe.pdf",
            file_path="tasks/test/remote-safe.pdf",
            file_url="/api/v1/attachments/test/download/",
            file_size=1234,
            mime_type="application/pdf",
            storage_provider="supabase",
        )
        mocked_provider = Mock()
        mocked_provider.generate_download_url.return_value = "https://example.com/signed"

        with patch("apps.attachments.services.get_attachment_storage_provider", return_value=mocked_provider):
            result = get_attachment_download(attachment=attachment, as_attachment=True)

        self.assertEqual(result.redirect_url, "https://example.com/signed")
