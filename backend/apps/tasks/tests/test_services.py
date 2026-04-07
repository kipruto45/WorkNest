from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.utils import timezone

from apps.integrations.models import EmailDelivery
from apps.memberships.models import Membership
from apps.tasks.models import SavedTaskView, Task, TaskTemplate
from apps.tasks.services import (
    assign_task,
    change_task_status,
    create_saved_task_view,
    create_task,
    create_task_from_template,
)
from apps.teams.models import Team

User = get_user_model()


class TaskServiceEmailTests(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(
            email="owner@example.com",
            password="StrongPass123!",
            name="Owner User",
        )
        self.member = User.objects.create_user(
            email="member@example.com",
            password="StrongPass123!",
            name="Member User",
        )
        self.manager = User.objects.create_user(
            email="manager@example.com",
            password="StrongPass123!",
            name="Manager User",
        )
        self.team = Team.objects.create(
            name="Platform",
            slug="platform-email-tests",
            description="Platform team",
            created_by=self.owner,
        )
        for user, role in (
            (self.owner, Membership.Role.ADMIN),
            (self.member, Membership.Role.MEMBER),
            (self.manager, Membership.Role.MANAGER),
        ):
            Membership.objects.create(
                user=user,
                team=self.team,
                role=role,
                status=Membership.Status.ACTIVE,
                invited_by=self.owner,
                joined_at=timezone.now(),
            )

    def test_create_task_sends_single_assignment_email(self) -> None:
        with self.captureOnCommitCallbacks(execute=True):
            create_task(
                team=self.team,
                title="Build release notes",
                created_by=self.owner,
                assigned_to=self.member,
            )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(EmailDelivery.objects.filter(email_type="task_assigned").count(), 1)

    def test_assign_task_sends_single_assignment_email(self) -> None:
        task = Task.objects.create(
            team=self.team,
            title="Review launch plan",
            created_by=self.owner,
        )

        with self.captureOnCommitCallbacks(execute=True):
            assign_task(task=task, user=self.manager, actor=self.owner)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(EmailDelivery.objects.filter(email_type="task_assigned").count(), 1)


class TaskServiceModernWorkflowTests(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(
            email="owner-modern@example.com",
            password="StrongPass123!",
            name="Owner User",
        )
        self.member = User.objects.create_user(
            email="member-modern@example.com",
            password="StrongPass123!",
            name="Member User",
        )
        self.team = Team.objects.create(
            name="Operations",
            slug="operations-modern",
            description="Operations team",
            created_by=self.owner,
        )
        for user, role in (
            (self.owner, Membership.Role.ADMIN),
            (self.member, Membership.Role.MEMBER),
        ):
            Membership.objects.create(
                user=user,
                team=self.team,
                role=role,
                status=Membership.Status.ACTIVE,
                invited_by=self.owner,
                joined_at=timezone.now(),
            )

    def test_create_task_from_template_applies_offsets(self) -> None:
        template = TaskTemplate.objects.create(
            team=self.team,
            name="weekly-ops-review",
            title="Weekly ops review",
            priority=Task.Priority.HIGH,
            estimated_minutes=60,
            planned_offset_days=1,
            due_offset_days=2,
            recurrence_pattern=Task.Recurrence.WEEKLY,
            recurrence_interval=1,
            assigned_to=self.member,
            created_by=self.owner,
        )

        task = create_task_from_template(template=template, actor=self.owner)

        self.assertEqual(task.source_template_id, template.id)
        self.assertEqual(task.assigned_to_id, self.member.id)
        self.assertEqual(task.planned_for_date, timezone.localdate() + timedelta(days=1))
        self.assertEqual(task.due_date.date(), timezone.localdate() + timedelta(days=2))

    def test_changing_done_status_spawns_next_recurring_task(self) -> None:
        task = create_task(
            team=self.team,
            title="Daily standup prep",
            created_by=self.owner,
            assigned_to=self.member,
            planned_for_date=timezone.localdate(),
            recurrence_pattern=Task.Recurrence.DAILY,
            recurrence_interval=1,
        )

        change_task_status(task=task, new_status=Task.Status.DONE, changed_by=self.owner)
        task.refresh_from_db()
        spawned_tasks = Task.objects.filter(team=self.team, title="Daily standup prep").exclude(pk=task.pk)

        self.assertEqual(spawned_tasks.count(), 1)
        self.assertFalse(task.is_recurring_active)
        self.assertEqual(spawned_tasks.first().planned_for_date, timezone.localdate() + timedelta(days=1))

    def test_create_saved_task_view_replaces_previous_default_for_same_scope(self) -> None:
        create_saved_task_view(
            user=self.owner,
            team=self.team,
            name="My day",
            layout=SavedTaskView.Layout.LIST,
            filters={"my_day": True},
            is_default=True,
        )
        newer_default = create_saved_task_view(
            user=self.owner,
            team=self.team,
            name="Blocked",
            layout=SavedTaskView.Layout.LIST,
            filters={"blocked": True},
            is_default=True,
        )

        defaults = SavedTaskView.objects.filter(
            user=self.owner,
            team=self.team,
            layout=SavedTaskView.Layout.LIST,
            is_default=True,
        )

        self.assertEqual(defaults.count(), 1)
        self.assertEqual(defaults.first().id, newer_default.id)
