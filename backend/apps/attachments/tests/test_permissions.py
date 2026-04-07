from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.attachments.models import Attachment
from apps.attachments.permissions import CanDeleteAttachment, CanUploadAttachment, CanViewAttachment
from apps.memberships.models import Membership
from apps.attachments.tests.utils import AttachmentFixtureMixin

User = get_user_model()


class AttachmentPermissionTests(AttachmentFixtureMixin, TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.factory = RequestFactory()
        self.attachment = Attachment.objects.create(
            task=self.task,
            uploaded_by=self.member,
            original_name="design.pdf",
            file_name="design-safe.pdf",
            file_path="tasks/test/design-safe.pdf",
            file_url="/api/v1/attachments/test/download/",
            file_size=2048,
            mime_type="application/pdf",
        )

    def build_request(self, user):
        request = self.factory.get("/")
        request.user = user
        return request

    def test_team_member_can_view_attachment(self) -> None:
        allowed = CanViewAttachment().has_object_permission(self.build_request(self.member), None, self.attachment)
        self.assertTrue(allowed)

    def test_outsider_cannot_view_attachment(self) -> None:
        allowed = CanViewAttachment().has_object_permission(self.build_request(self.outsider), None, self.attachment)
        self.assertFalse(allowed)

    def test_member_can_delete_own_attachment(self) -> None:
        allowed = CanDeleteAttachment().has_object_permission(self.build_request(self.member), None, self.attachment)
        self.assertTrue(allowed)

    def test_manager_can_delete_team_attachment(self) -> None:
        allowed = CanDeleteAttachment().has_object_permission(self.build_request(self.manager), None, self.attachment)
        self.assertTrue(allowed)

    def test_regular_member_cannot_delete_other_users_attachment(self) -> None:
        second_member = User.objects.create_user(
            email="second-member@example.com",
            password="StrongPass123!",
            name="Second Member",
        )
        Membership.objects.create(
            user=second_member,
            team=self.team,
            role=Membership.Role.MEMBER,
            status=Membership.Status.ACTIVE,
            invited_by=self.owner,
            joined_at=self.task.created_at,
        )
        allowed = CanDeleteAttachment().has_object_permission(self.build_request(second_member), None, self.attachment)
        self.assertFalse(allowed)

    def test_archived_task_cannot_accept_uploads(self) -> None:
        self.task.is_archived = True
        self.task.save(update_fields=["is_archived", "updated_at"])

        allowed = CanUploadAttachment().has_object_permission(self.build_request(self.member), None, self.task)

        self.assertFalse(allowed)
