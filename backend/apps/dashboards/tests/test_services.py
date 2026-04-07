from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.comments.models import Comment
from apps.audit_logs.constants import AuditAction
from apps.audit_logs.models import AuditLog
from apps.dashboards.services import (
    build_admin_dashboard_snapshot,
    build_member_activity_metrics,
    build_personal_dashboard_summary,
    build_priority_distribution,
    build_status_distribution,
    build_team_dashboard_summary,
    build_team_progress_metrics,
    build_workload_distribution,
)
from apps.memberships.models import Membership
from apps.tasks.models import Task
from apps.teams.models import Team

User = get_user_model()


class DashboardServiceTests(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(email="owner@example.com", password="StrongPass123!", name="Owner")
        self.member = User.objects.create_user(email="member@example.com", password="StrongPass123!", name="Member")
        self.teammate = User.objects.create_user(email="mate@example.com", password="StrongPass123!", name="Mate")
        self.team = Team.objects.create(
            name="Backend",
            slug="backend",
            description="Backend team",
            created_by=self.owner,
        )
        for user, role in (
            (self.owner, Membership.Role.ADMIN),
            (self.member, Membership.Role.MEMBER),
            (self.teammate, Membership.Role.MEMBER),
        ):
            Membership.objects.create(
                team=self.team,
                user=user,
                role=role,
                status=Membership.Status.ACTIVE,
                invited_by=self.owner,
                joined_at=timezone.now(),
            )
        now = timezone.now()
        start_of_week = now - timedelta(days=now.weekday())
        completed_this_week_at = start_of_week.replace(hour=9, minute=0, second=0, microsecond=0)

        self.done_task = Task.objects.create(
            team=self.team,
            title="Ship auth",
            created_by=self.owner,
            assigned_to=self.member,
            status=Task.Status.DONE,
            priority=Task.Priority.HIGH,
            due_date=now - timedelta(days=1),
            completed_at=completed_this_week_at,
        )
        self.overdue_task = Task.objects.create(
            team=self.team,
            title="Fix API docs",
            created_by=self.owner,
            assigned_to=self.member,
            status=Task.Status.IN_PROGRESS,
            priority=Task.Priority.CRITICAL,
            due_date=now - timedelta(hours=6),
        )
        self.todo_task = Task.objects.create(
            team=self.team,
            title="Refactor selectors",
            created_by=self.owner,
            assigned_to=self.teammate,
            status=Task.Status.TODO,
            priority=Task.Priority.MEDIUM,
            due_date=now + timedelta(days=3),
        )
        Comment.objects.create(task=self.overdue_task, author=self.member, content="Updating this now")
        AuditLog.objects.create(
            actor=self.owner,
            action=AuditAction.TEAM_CREATED,
            target_type="team",
            target_id=str(self.team.id),
            target_repr=self.team.name,
            team=self.team,
        )
        AuditLog.objects.create(
            actor=self.member,
            action=AuditAction.USER_LOGGED_IN,
            target_type="user",
            target_id=str(self.member.id),
            target_repr=self.member.email,
            team=self.team,
        )

    def test_personal_dashboard_summary_returns_core_metrics(self) -> None:
        summary = build_personal_dashboard_summary(user=self.member, reference_time=timezone.now())

        self.assertEqual(summary["summary"]["assigned_tasks"], 2)
        self.assertEqual(summary["summary"]["overdue_tasks"], 1)
        self.assertEqual(summary["summary"]["completed_this_week"], 1)
        self.assertEqual(summary["summary"]["completion_rate"], 50.0)

    def test_team_dashboard_summary_returns_completion_and_member_activity(self) -> None:
        summary = build_team_dashboard_summary(team=self.team, reference_time=timezone.now())

        self.assertEqual(summary["summary"]["total_tasks"], 3)
        self.assertEqual(summary["summary"]["completed_tasks"], 1)
        self.assertEqual(summary["summary"]["pending_tasks"], 2)
        self.assertEqual(summary["summary"]["completion_rate"], 33.33)
        self.assertEqual(len(summary["member_activity"]), 3)

    def test_team_progress_metrics_include_progress_bar(self) -> None:
        progress = build_team_progress_metrics(team=self.team, reference_time=timezone.now())

        self.assertEqual(progress["progress_bar"]["completed"], 1)
        self.assertEqual(progress["progress_bar"]["total"], 3)
        self.assertEqual(progress["progress_bar"]["percentage"], 33.33)

    def test_member_activity_metrics_include_comments_and_rates(self) -> None:
        activity = build_member_activity_metrics(team=self.team, reference_time=timezone.now())
        member_row = next(item for item in activity if item["user_id"] == self.member.id)

        self.assertEqual(member_row["assigned_tasks"], 2)
        self.assertEqual(member_row["completed_tasks"], 1)
        self.assertEqual(member_row["comment_count"], 1)
        self.assertEqual(member_row["completion_rate"], 50.0)

    def test_status_and_priority_distribution_return_frontend_ready_data(self) -> None:
        status_distribution = build_status_distribution(team=self.team)
        priority_distribution = build_priority_distribution(team=self.team)

        done_row = next(item for item in status_distribution if item["status"] == Task.Status.DONE)
        critical_row = next(item for item in priority_distribution if item["priority"] == Task.Priority.CRITICAL)

        self.assertEqual(done_row["count"], 1)
        self.assertEqual(done_row["percentage"], 33.33)
        self.assertEqual(critical_row["count"], 1)

    def test_workload_distribution_tracks_open_and_overdue_tasks(self) -> None:
        workload = build_workload_distribution(team=self.team, reference_time=timezone.now())
        member_row = next(item for item in workload if item["user_id"] == self.member.id)

        self.assertEqual(member_row["open_tasks"], 1)
        self.assertEqual(member_row["overdue_tasks"], 1)

    def test_admin_dashboard_snapshot_returns_platform_sections(self) -> None:
        snapshot = build_admin_dashboard_snapshot(reference_time=timezone.now())

        self.assertIn("overview", snapshot)
        self.assertIn("growth", snapshot)
        self.assertIn("team_health", snapshot)
        self.assertEqual(snapshot["overview"]["total_users"], 3)
        self.assertEqual(snapshot["overview"]["total_tasks"], 3)
        self.assertTrue(snapshot["system_events"])
