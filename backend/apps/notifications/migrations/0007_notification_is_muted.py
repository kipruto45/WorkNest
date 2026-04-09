from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0006_rename_admin_commun_audien_4d02be_idx_admin_commu_audienc_c522c2_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="notification",
            name="is_muted",
            field=models.BooleanField(default=False),
        ),
    ]

