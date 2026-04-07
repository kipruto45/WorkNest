from __future__ import annotations

from django.test import TestCase

from apps.attachments.models import Attachment
from apps.attachments.tests.utils import AttachmentFixtureMixin


class AttachmentModelTests(AttachmentFixtureMixin, TestCase):
    def test_soft_delete_marks_attachment_without_removing_record(self) -> None:
        attachment = Attachment.objects.create(
            task=self.task,
            uploaded_by=self.owner,
            original_name="brief.pdf",
            file_name="stored-brief.pdf",
            file_path="tasks/test/stored-brief.pdf",
            file_url="/api/v1/attachments/test/download/",
            file_size=1234,
            mime_type="application/pdf",
        )

        attachment.soft_delete()
        attachment.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
        attachment.refresh_from_db()

        self.assertEqual(str(attachment), "brief.pdf")
        self.assertTrue(attachment.is_deleted)
        self.assertIsNotNone(attachment.deleted_at)
        self.assertEqual(Attachment.objects.active().count(), 0)
