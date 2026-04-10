from __future__ import annotations

from django.test import TestCase

from apps.comments.models import Comment
from apps.realtime.serializers import build_comment_event_data
from apps.realtime.tests.utils import RealtimeFixtureMixin


class RealtimeSerializerTests(RealtimeFixtureMixin, TestCase):
    def test_build_comment_event_data_includes_parent_id_when_present(self) -> None:
        parent = Comment.objects.create(
            task=self.task,
            author=self.owner,
            content="Parent comment",
        )
        child = Comment.objects.create(
            task=self.task,
            author=self.member,
            content="Child comment",
            parent=parent,
        )

        payload = build_comment_event_data(comment=child)

        self.assertEqual(payload["comment_id"], str(child.id))
        self.assertEqual(payload["parent_id"], str(parent.id))
        self.assertEqual(payload["task_id"], str(self.task.id))
        self.assertEqual(payload["team_id"], str(self.team.id))

    def test_build_comment_event_data_allows_null_parent_id(self) -> None:
        comment = Comment.objects.create(
            task=self.task,
            author=self.owner,
            content="Standalone comment",
        )

        payload = build_comment_event_data(comment=comment)

        self.assertIsNone(payload["parent_id"])
