from __future__ import annotations

import django.db.models.deletion
import uuid

from django.conf import settings
from django.db import migrations, models

import apps.memberships.models


class Migration(migrations.Migration):
    dependencies = [
        ("teams", "0006_teamannouncement_archived_at_and_more"),
        ("memberships", "0002_teaminvitation_accepted_at_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TeamInviteLink",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "role",
                    models.CharField(
                        choices=[("admin", "Admin"), ("manager", "Manager"), ("member", "Member")],
                        default="member",
                        max_length=20,
                    ),
                ),
                ("token", models.CharField(default=apps.memberships.models._generate_secure_token, max_length=255, unique=True)),
                ("label", models.CharField(blank=True, max_length=255)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("max_uses", models.PositiveIntegerField(blank=True, null=True)),
                ("current_uses", models.PositiveIntegerField(default=0)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="created_team_invite_links",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "team",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="invite_links",
                        to="teams.team",
                    ),
                ),
            ],
            options={
                "db_table": "team_invite_links",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="teaminvitelink",
            index=models.Index(fields=["team", "is_active"], name="team_invite_team_id_7fce6e_idx"),
        ),
        migrations.AddIndex(
            model_name="teaminvitelink",
            index=models.Index(fields=["team", "role"], name="team_invite_team_id_5eec61_idx"),
        ),
        migrations.AddIndex(
            model_name="teaminvitelink",
            index=models.Index(fields=["expires_at"], name="team_invite_expires_2dd94f_idx"),
        ),
        migrations.AddIndex(
            model_name="teaminvitelink",
            index=models.Index(fields=["created_at"], name="team_invite_created_9c2070_idx"),
        ),
    ]
