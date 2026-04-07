from __future__ import annotations

import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="EmailDelivery",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("email_type", models.CharField(max_length=64)),
                ("template_name", models.CharField(max_length=120)),
                ("recipient_email", models.EmailField(max_length=254)),
                ("subject", models.CharField(max_length=255)),
                ("provider", models.CharField(blank=True, max_length=32)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("processing", "Processing"),
                            ("sent", "Sent"),
                            ("failed", "Failed"),
                            ("skipped", "Skipped"),
                        ],
                        default="queued",
                        max_length=20,
                    ),
                ),
                ("source", models.CharField(blank=True, max_length=64)),
                ("dedupe_key", models.CharField(blank=True, max_length=255)),
                ("related_object_type", models.CharField(blank=True, max_length=64)),
                ("related_object_id", models.CharField(blank=True, max_length=64)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("provider_response", models.JSONField(blank=True, default=dict)),
                ("provider_message_id", models.CharField(blank=True, max_length=255)),
                ("celery_task_id", models.CharField(blank=True, max_length=255)),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                ("last_error", models.TextField(blank=True)),
                ("last_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "email_deliveries",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="emaildelivery",
            index=models.Index(fields=["status", "created_at"], name="email_deliv_status_17e4f0_idx"),
        ),
        migrations.AddIndex(
            model_name="emaildelivery",
            index=models.Index(fields=["email_type", "created_at"], name="email_deliv_email_t_fb9145_idx"),
        ),
        migrations.AddIndex(
            model_name="emaildelivery",
            index=models.Index(fields=["recipient_email", "created_at"], name="email_deliv_recipie_7e6656_idx"),
        ),
        migrations.AddIndex(
            model_name="emaildelivery",
            index=models.Index(fields=["dedupe_key"], name="email_deliv_dedupe__e3874e_idx"),
        ),
        migrations.AddIndex(
            model_name="emaildelivery",
            index=models.Index(
                fields=["related_object_type", "related_object_id"],
                name="email_deliv_related_bf7f77_idx",
            ),
        ),
    ]
