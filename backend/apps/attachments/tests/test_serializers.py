from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from apps.attachments.serializers import AttachmentUploadSerializer


class AttachmentSerializerTests(TestCase):
    def test_upload_serializer_accepts_valid_pdf(self) -> None:
        serializer = AttachmentUploadSerializer(
            data={
                "file": SimpleUploadedFile(
                    "requirements.pdf",
                    b"%PDF-1.4 attachment",
                    content_type="application/pdf",
                )
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["file_metadata"]["mime_type"], "application/pdf")

    def test_upload_serializer_rejects_empty_file(self) -> None:
        serializer = AttachmentUploadSerializer(
            data={
                "file": SimpleUploadedFile(
                    "empty.pdf",
                    b"",
                    content_type="application/pdf",
                )
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("file", serializer.errors)

    def test_upload_serializer_rejects_invalid_extension(self) -> None:
        serializer = AttachmentUploadSerializer(
            data={
                "file": SimpleUploadedFile(
                    "script.exe",
                    b"MZ",
                    content_type="application/octet-stream",
                )
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("file", serializer.errors)

    @override_settings(ATTACHMENTS_MAX_FILE_SIZE=4)
    def test_upload_serializer_rejects_oversized_file(self) -> None:
        serializer = AttachmentUploadSerializer(
            data={
                "file": SimpleUploadedFile(
                    "large.txt",
                    b"too-large",
                    content_type="text/plain",
                )
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn("file", serializer.errors)
