import uuid

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("authentication", "0003_alter_loginactivity_email_phoneverificationcode"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CredentialChangeRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("credential_type", models.CharField(choices=[("email", "Email"), ("phone", "Phone")], max_length=16)),
                ("current_value", models.CharField(blank=True, max_length=255)),
                ("new_value", models.CharField(max_length=255)),
                ("code", models.CharField(max_length=6)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                ("attempt_count", models.PositiveIntegerField(default=0)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="credential_change_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "db_table": "credential_change_requests",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="credentialchangerequest",
            index=models.Index(fields=["user", "credential_type", "expires_at"], name="credentialc_user_id_d8827a_idx"),
        ),
        migrations.AddIndex(
            model_name="credentialchangerequest",
            index=models.Index(fields=["new_value", "credential_type", "expires_at"], name="credentialc_new_val_6256f6_idx"),
        ),
        migrations.AddIndex(
            model_name="credentialchangerequest",
            index=models.Index(fields=["current_value", "credential_type", "used_at"], name="credentialc_current_67725d_idx"),
        ),
    ]
