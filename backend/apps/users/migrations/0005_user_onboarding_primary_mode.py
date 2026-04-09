from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0004_user_account_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="primary_mode",
            field=models.CharField(choices=[("personal", "Personal"), ("team", "Team")], default="personal", max_length=20),
        ),
        migrations.AddField(
            model_name="user",
            name="onboarding_completed",
            field=models.BooleanField(default=False),
        ),
    ]
