from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0004_location")]

    operations = [
        migrations.AddField("savedevent", "title", models.CharField(blank=True, max_length=200)),
        migrations.AddField("savedevent", "start_time_utc", models.DateTimeField(blank=True, null=True)),
        migrations.AddField("savedevent", "end_time_utc", models.DateTimeField(blank=True, null=True)),
        migrations.AddField("savedevent", "timezone", models.CharField(blank=True, max_length=63)),
        migrations.AddField("savedevent", "location_label", models.CharField(blank=True, max_length=120)),
    ]
