from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.comments.models import Comment
from apps.dashboards.selectors import (
    get_team_deadline_feed,
    get_team_member_activity,
    get_team_priority_counts,
    get_team_status_counts,
    get_user_completed_tasks_this_week,
    get_user_overdue_tasks,
)
from apps.memberships.models import Membership
from apps.tasks.models import Task
from apps.teams.models import Team

User = get_user_model()


class DashboardSelectorTests(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        self.member = User.objects.create_user(email="member@example.com", password="StrongPass123!", name="Member")
        self.other_user = User.objects.create_user(email="other@example.com", password="StrongPass123!", name="Other")
        self.team = Team.objects.create(
            name="Platform",
            slug="platform",
            description="Platform team",
            created_by=self.owner,
        )
        self.other_team = Team.objects.create(
            name="Support",
            slug="support",
            description="Support team",
            created_by=self.other_user,
        )
        for user, role in ((self.owner, Membership.Role.ADMIN), (self.member, Membership.Role.MEMBER)):
            Membership.objects.create(
                team=self.team,
                user=user,
                role=role,
                status=Membership.Status.ACTIVE,
                invited_by=self.owner,
                joined_at=timezone.now(),
            )
        Membership.objects.create(
            team=self.other_team,
            user=self.other_user,
            role=Membership.Role.ADMIN,
            status=Membership.Status.ACTIVE,
            invited_by=self.other_user,
            joined_at=timezone.now(),
        )
        now = timezone.now()
        start_of_week = now - timedelta(days=now.weekday())
        completed_this_week_at = start_of_week.replace(hour=9, minute=0, second=0, microsecond=0)

        self.done_task = Task.objects.create(
            team=self.team,
            title="Done task",
            created_by=self.owner,
            assigned_to=self.member,
            status=Task.Status.DONE,
            priority=Task.Priority.HIGH,
            due_date=now - timedelta(days=1),
            completed_at=completed_this_week_at,
        )
        self.overdue_task = Task.objects.create(
            team=self.team,
            title="Overdue task",
            created_by=self.owner,
            assigned_to=self.member,
            status=Task.Status.IN_PROGRESS,
            priority=Task.Priority.CRITICAL,
            due_date=now - timedelta(hours=3),
        )
        self.upcoming_task = Task.objects.create(
            team=self.team,
            title="Upcoming task",
            created_by=self.owner,
            assigned_to=self.member,
            status=Task.Status.TODO,
            priority=Task.Priority.MEDIUM,
            due_date=now + timedelta(days=2),
        )
        self.other_team_task = Task.objects.create(
            team=self.other_team,
            title="Other team task",
            created_by=self.other_user,
            assigned_to=self.other_user,
            status=Task.Status.TODO,
            priority=Task.Priority.LOW,
            due_date=now + timedelta(days=4),
        )
        Comment.objects.create(task=self.overdue_task, author=self.member, content="Working on it")

    def test_user_overdue_tasks_only_include_non_done_items(self) -> None:
        task_ids = {task.id for task in get_user_overdue_tasks(self.member)}

        self.assertIn(self.overdue_task.id, task_ids)
        self.assertNotIn(self.done_task.id, task_ids)

    def test_user_completed_tasks_this_week_uses_completed_at(self) -> None:
        task_ids = {task.id for task in get_user_completed_tasks_this_week(self.member)}

        self.assertIn(self.done_task.id, task_ids)
        self.assertNotIn(self.overdue_task.id, task_ids)

    def test_team_status_and_priority_counts_are_scoped_to_team(self) -> None:
        status_counts = {item["status"]: item["count"] for item in get_team_status_counts(self.team)}
        priority_counts = {item["priority"]: item["count"] for item in get_team_priority_counts(self.team)}

        self.assertEqual(status_counts[Task.Status.DONE], 1)
        self.assertEqual(status_counts[Task.Status.IN_PROGRESS], 1)
        self.assertEqual(status_counts[Task.Status.TODO], 1)
        self.assertNotIn(Task.Priority.LOW, priority_counts)
        self.assertEqual(priority_counts[Task.Priority.CRITICAL], 1)

    def test_team_member_activity_includes_task_and_comment_metrics(self) -> None:
        activity = list(get_team_member_activity(self.team))
        member_row = next(item for item in activity if item.user_id == self.member.id)

        self.assertEqual(member_row.assigned_count, 3)
        self.assertEqual(member_row.completed_count, 1)
        self.assertEqual(member_row.overdue_count, 1)
        self.assertEqual(member_row.comment_count, 1)

    def test_team_deadline_feed_can_filter_by_status(self) -> None:
        task_ids = {
            task.id
            for task in get_team_deadline_feed(
                self.team,
                status=Task.Status.TODO,
            )
        }

        self.assertEqual(task_ids, {self.upcoming_task.id})
