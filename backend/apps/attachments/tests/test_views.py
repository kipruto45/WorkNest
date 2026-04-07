from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.attachments.models import Attachment
from apps.attachments.services import upload_attachment
from apps.attachments.tests.utils import AttachmentFixtureMixin, TemporaryMediaRootMixin


class AttachmentEndpointTests(TemporaryMediaRootMixin, AttachmentFixtureMixin, APITestCase):
    def test_team_member_can_upload_and_list_task_attachments(self) -> None:
        self.authenticate(self.member)

        upload_response = self.client.post(
            reverse("api_v1:attachments:task-list-create", args=[self.task.id]),
            {
                "file": SimpleUploadedFile(
                    "requirements.pdf",
                    b"%PDF-1.4 upload view",
                    content_type="application/pdf",
                )
            },
            format="multipart",
        )

        self.assertEqual(upload_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(upload_response.data["data"]["original_name"], "requirements.pdf")

        list_response = self.client.get(reverse("api_v1:attachments:task-list-create", args=[self.task.id]))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data["data"]), 1)
        self.assertIn("/api/v1/attachments/", list_response.data["data"][0]["file_url"])

    def test_outsider_cannot_upload_attachment_to_foreign_task(self) -> None:
        self.authenticate(self.outsider)

        response = self.client.post(
            reverse("api_v1:attachments:task-list-create", args=[self.task.id]),
            {
                "file": SimpleUploadedFile(
                    "blocked.pdf",
                    b"%PDF-1.4 blocked",
                    content_type="application/pdf",
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_upload_rejects_invalid_file_type(self) -> None:
        self.authenticate(self.member)

        response = self.client.post(
            reverse("api_v1:attachments:task-list-create", args=[self.task.id]),
            {
                "file": SimpleUploadedFile(
                    "malware.exe",
                    b"MZ",
                    content_type="application/octet-stream",
                )
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data["errors"])

    def test_member_can_view_attachment_detail_and_download(self) -> None:
        attachment = upload_attachment(
            task=self.task,
            uploaded_by=self.member,
            file_obj=SimpleUploadedFile(
                "detail.pdf",
                b"%PDF-1.4 detail",
                content_type="application/pdf",
            ),
        )

        self.authenticate(self.member)

        detail_response = self.client.get(reverse("api_v1:attachments:detail", args=[attachment.id]))
        download_response = self.client.get(reverse("api_v1:attachments:download", args=[attachment.id]))

        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(download_response.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(download_response.streaming_content), b"%PDF-1.4 detail")

    def test_manager_can_delete_other_users_attachment(self) -> None:
        self.authenticate(self.member)
        upload_response = self.client.post(
            reverse("api_v1:attachments:task-list-create", args=[self.task.id]),
            {
                "file": SimpleUploadedFile(
                    "delete.pdf",
                    b"%PDF-1.4 delete",
                    content_type="application/pdf",
                )
            },
            format="multipart",
        )
        attachment_id = upload_response.data["data"]["id"]

        self.authenticate(self.manager)
        delete_response = self.client.delete(reverse("api_v1:attachments:detail", args=[attachment_id]))

        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Attachment.objects.active().filter(pk=attachment_id).exists())

    def test_deleted_attachment_is_not_returned_to_members(self) -> None:
        attachment = Attachment.objects.create(
            task=self.task,
            uploaded_by=self.member,
            original_name="deleted.pdf",
            file_name="deleted-safe.pdf",
            file_path="tasks/test/deleted-safe.pdf",
            file_url="/api/v1/attachments/test/download/",
            file_size=512,
            mime_type="application/pdf",
            is_deleted=True,
        )
        self.authenticate(self.member)

        response = self.client.get(reverse("api_v1:attachments:detail", args=[attachment.id]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
