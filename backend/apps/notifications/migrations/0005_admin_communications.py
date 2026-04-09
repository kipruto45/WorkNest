from django.conf import settings
from django.db import migrations, models
import django.utils.timezone
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0004_alter_notification_type"),
        ("integrations", "0002_rename_email_deliv_status_17e4f0_idx_email_deliv_status_44280d_idx_and_more"),
        ("teams", "0005_team_is_personal"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AdminCommunication",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=255)),
                ("message", models.TextField()),
                ("audience_type", models.CharField(choices=[("single_user", "Single User"), ("selected_users", "Selected Users"), ("single_team", "Single Team"), ("selected_teams", "Selected Teams"), ("all_users", "All Users")], max_length=32)),
                ("channel_type", models.CharField(choices=[("in_app", "In-App"), ("email", "Email"), ("both", "Email + In-App")], max_length=16)),
                ("status", models.CharField(choices=[("scheduled", "Scheduled"), ("sent", "Sent"), ("failed", "Failed")], default="sent", max_length=16)),
                ("scheduled_for", models.DateTimeField(blank=True, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("cta_label", models.CharField(blank=True, max_length=120)),
                ("cta_link", models.URLField(blank=True, max_length=500)),
                ("audience_metadata", models.JSONField(blank=True, default=dict)),
                ("recipient_count", models.PositiveIntegerField(default=0)),
                ("delivered_in_app_count", models.PositiveIntegerField(default=0)),
                ("delivered_email_count", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_admin_communications", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "admin_communications",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="AdminCommunicationRecipient",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("channel_type", models.CharField(choices=[("in_app", "In-App"), ("email", "Email"), ("both", "Email + In-App")], max_length=16)),
                ("in_app_sent", models.BooleanField(default=False)),
                ("email_sent", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("communication", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recipients", to="notifications.admincommunication")),
                ("email_delivery", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="admin_communication_recipients", to="integrations.emaildelivery")),
                ("team", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="admin_communication_recipients", to="teams.team")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="admin_communication_recipients", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "admin_communication_recipients",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="admincommunication",
            index=models.Index(fields=["audience_type", "created_at"], name="admin_commun_audien_4d02be_idx"),
        ),
        migrations.AddIndex(
            model_name="admincommunication",
            index=models.Index(fields=["channel_type", "created_at"], name="admin_commun_channe_95d93c_idx"),
        ),
        migrations.AddIndex(
            model_name="admincommunication",
            index=models.Index(fields=["status", "created_at"], name="admin_commun_status_6fa795_idx"),
        ),
        migrations.AddConstraint(
            model_name="admincommunicationrecipient",
            constraint=models.UniqueConstraint(fields=("communication", "user"), name="unique_admin_comm_recipient"),
        ),
        migrations.AddIndex(
            model_name="admincommunicationrecipient",
            index=models.Index(fields=["communication", "created_at"], name="admin_commu_commun_f2b4a4_idx"),
        ),
        migrations.AddIndex(
            model_name="admincommunicationrecipient",
            index=models.Index(fields=["user", "created_at"], name="admin_commu_user_id_3f2e2a_idx"),
        ),
        migrations.AddIndex(
            model_name="admincommunicationrecipient",
            index=models.Index(fields=["team", "created_at"], name="admin_commu_team_id_678b99_idx"),
        ),
    ]
