from django.db import migrations, models

import accounts.models


def require_empty_user_table(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    if User.objects.exists():
        raise RuntimeError(
            "Existing users need ZIP codes and birth dates before this migration can run. "
            "Backfill those values in a dedicated data migration."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(require_empty_user_table, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="zip_code",
            field=models.CharField(max_length=10),
        ),
        migrations.AddField(
            model_name="user",
            name="birth_date",
            field=models.DateField(validators=[accounts.models.validate_birth_date]),
        ),
    ]
