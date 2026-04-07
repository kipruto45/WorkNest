from __future__ import annotations

from django.test import TestCase

from apps.audit_logs.constants import AuditAction
from apps.audit_logs.models import AuditLog
from apps.audit_logs.tests.utils import AuditLogFixtureMixin


class AuditLogModelTests(AuditLogFixtureMixin, TestCase):
    def test_audit_log_creation_persists_actor_team_and_metadata(self) -> None:
        audit_log = AuditLog.objects.create(
            actor=self.owner,
            action=AuditAction.TASK_CREATED,
            target_type="task",
            target_id=str(self.task.id),
            target_repr=self.task.title,
            team=self.team,
            metadata={"status": "todo"},
        )

        self.assertEqual(str(audit_log), f"{AuditAction.TASK_CREATED} (task:{self.task.id})")
        self.assertEqual(audit_log.actor, self.owner)
        self.assertEqual(audit_log.team, self.team)
        self.assertEqual(audit_log.metadata["status"], "todo")
