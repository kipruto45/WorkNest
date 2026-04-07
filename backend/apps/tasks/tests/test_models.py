from __future__ import annotations

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.memberships.models import Membership
from apps.tasks.models import Task
from apps.tasks.services import archive_task
from apps.teams.models import Team

User = get_user_model()


class TaskModelTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="StrongPass123!",
            name="Owner User",
        )
        self.team = Team.objects.create(
            name="Platform",
            slug="platform",
            description="Core platform team",
            created_by=self.user,
        )
        Membership.objects.create(
            user=self.user,
            team=self.team,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE,
            invited_by=self.user,
            joined_at=timezone.now(),
        )

    def test_task_defaults_and_overdue_flag(self) -> None:
        task = Task.objects.create(
            team=self.team,
            title="Ship task module",
            created_by=self.user,
            due_date=timezone.now() - timedelta(hours=2),
        )

        self.assertEqual(task.status, Task.Status.TODO)
        self.assertEqual(task.priority, Task.Priority.MEDIUM)
        self.assertTrue(task.is_overdue)

    def test_done_task_is_not_overdue(self) -> None:
        task = Task.objects.create(
            team=self.team,
            title="Closed task",
            created_by=self.user,
            due_date=timezone.now() - timedelta(days=1),
            status=Task.Status.DONE,
            completed_at=timezone.now(),
        )

        self.assertFalse(task.is_overdue)

    def test_archived_task_is_not_overdue(self) -> None:
        task = Task.objects.create(
            team=self.team,
            title="Archive me",
            created_by=self.user,
            due_date=timezone.now() - timedelta(days=1),
        )

        archive_task(task=task)
        task.refresh_from_db()

        self.assertTrue(task.is_archived)
        self.assertIsNotNone(task.archived_at)
        self.assertFalse(task.is_overdue)

    def test_monthly_recurring_task_shifts_dates_safely(self) -> None:
        task = Task.objects.create(
            team=self.team,
            title="Monthly review",
            created_by=self.user,
            recurrence_pattern=Task.Recurrence.MONTHLY,
            recurrence_interval=1,
            planned_for_date=date(2026, 1, 31),
            due_date=timezone.make_aware(timezone.datetime(2026, 1, 31, 17, 0)),
        )

        next_planned_for_date, next_due_date = task.build_next_recurrence_dates()

        self.assertEqual(next_planned_for_date, date(2026, 2, 28))
        self.assertEqual(next_due_date.date(), date(2026, 2, 28))
