from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("comments", "0004_commentreaction_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="comment",
            name="guest_name",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="comment",
            name="guest_email",
            field=models.EmailField(blank=True, max_length=254),
        ),
    ]
