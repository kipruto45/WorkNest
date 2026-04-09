from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tasks", "0006_task_dependencies_milestones_time_tracking"),
    ]

    operations = [
        migrations.AddField(
            model_name="savedtaskview",
            name="is_shared",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="savedtaskview",
            name="is_pinned",
            field=models.BooleanField(default=False),
        ),
        migrations.AddIndex(
            model_name="savedtaskview",
            index=models.Index(fields=["user", "is_pinned"], name="saved_task_user_is_pinned_idx"),
        ),
        migrations.AddIndex(
            model_name="savedtaskview",
            index=models.Index(fields=["team", "is_pinned"], name="saved_task_team_is_pinned_idx"),
        ),
    ]

