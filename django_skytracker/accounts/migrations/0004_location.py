from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0003_saved_event"),
    ]

    operations = [
        migrations.CreateModel(
            name="Location",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=120)),
                ("latitude", models.DecimalField(decimal_places=5, max_digits=8)),
                ("longitude", models.DecimalField(decimal_places=5, max_digits=8)),
                ("elevation_meters", models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ("timezone", models.CharField(default="UTC", max_length=63)),
                ("source", models.CharField(default="manual", max_length=40)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="locations", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("label", "created_at")},
        ),
        migrations.AddConstraint(
            model_name="location",
            constraint=models.UniqueConstraint(fields=("owner", "label"), name="accounts_location_owner_label_unique"),
        ),
    ]
