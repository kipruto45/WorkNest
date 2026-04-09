from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0005_task_start_at"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("teams", "0005_team_is_personal"),
    ]

    operations = [
        migrations.CreateModel(
            name="Milestone",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("planned", "Planned"), ("in_progress", "In Progress"), ("completed", "Completed")], default="planned", max_length=20)),
                ("due_date", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_milestones", to=settings.AUTH_USER_MODEL)),
                ("team", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="milestones", to="teams.team")),
            ],
            options={
                "db_table": "milestones",
                "ordering": ["-due_date", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="TaskDependency",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("dependency_type", models.CharField(choices=[("blocks", "Blocks"), ("related", "Related")], default="blocks", max_length=20)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("from_task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="outgoing_dependencies", to="tasks.task")),
                ("to_task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="incoming_dependencies", to="tasks.task")),
            ],
            options={
                "db_table": "task_dependencies",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="TimeEntry",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("start_time", models.DateTimeField()),
                ("end_time", models.DateTimeField(blank=True, null=True)),
                ("duration_seconds", models.PositiveIntegerField(default=0)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="time_entries", to="tasks.task")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="time_entries", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "time_entries",
                "ordering": ["-start_time"],
            },
        ),
        migrations.CreateModel(
            name="AutomationRule",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=255)),
                ("trigger_type", models.CharField(choices=[("task_created", "Task Created"), ("task_assigned", "Task Assigned"), ("task_status_changed", "Task Status Changed"), ("task_overdue", "Task Overdue"), ("invite_accepted", "Invite Accepted"), ("milestone_overdue", "Milestone Overdue")], max_length=32)),
                ("conditions", models.JSONField(blank=True, default=dict)),
                ("action_type", models.CharField(choices=[("create_notification", "Create Notification"), ("send_email", "Send Email"), ("assign_user", "Assign User"), ("change_status", "Change Status"), ("add_label", "Add Label"), ("create_follow_up_task", "Create Follow-up Task")], max_length=40)),
                ("action_payload", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_automation_rules", to=settings.AUTH_USER_MODEL)),
                ("team", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="automation_rules", to="teams.team")),
            ],
            options={
                "db_table": "automation_rules",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="GuestTaskAccess",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email", models.EmailField(max_length=254)),
                ("token", models.CharField(max_length=64, unique=True)),
                ("permission", models.CharField(choices=[("view", "View"), ("comment", "Comment")], default="view", max_length=16)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("invited_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="guest_task_invites", to=settings.AUTH_USER_MODEL)),
                ("task", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="guest_access", to="tasks.task")),
            ],
            options={
                "db_table": "guest_task_access",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddField(
            model_name="task",
            name="milestone",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="tasks", to="tasks.milestone"),
        ),
        migrations.AddIndex(
            model_name="milestone",
            index=models.Index(fields=["team", "status"], name="milestones_team_id_status_idx"),
        ),
        migrations.AddIndex(
            model_name="milestone",
            index=models.Index(fields=["team", "due_date"], name="milestones_team_id_due_date_idx"),
        ),
        migrations.AddIndex(
            model_name="taskdependency",
            index=models.Index(fields=["from_task", "dependency_type"], name="task_depend_from_task_dep_type_idx"),
        ),
        migrations.AddIndex(
            model_name="taskdependency",
            index=models.Index(fields=["to_task", "dependency_type"], name="task_depend_to_task_dep_type_idx"),
        ),
        migrations.AddConstraint(
            model_name="taskdependency",
            constraint=models.UniqueConstraint(fields=("from_task", "to_task", "dependency_type"), name="unique_task_dependency"),
        ),
        migrations.AddIndex(
            model_name="timeentry",
            index=models.Index(fields=["task", "start_time"], name="time_entries_task_start_idx"),
        ),
        migrations.AddIndex(
            model_name="timeentry",
            index=models.Index(fields=["user", "start_time"], name="time_entries_user_start_idx"),
        ),
        migrations.AddIndex(
            model_name="automationrule",
            index=models.Index(fields=["team", "trigger_type", "is_active"], name="automation_rule_team_trigger_active_idx"),
        ),
        migrations.AddIndex(
            model_name="guesttaskaccess",
            index=models.Index(fields=["task", "created_at"], name="guest_task_access_task_created_idx"),
        ),
        migrations.AddIndex(
            model_name="guesttaskaccess",
            index=models.Index(fields=["email", "created_at"], name="guest_task_access_email_created_idx"),
        ),
    ]
