from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .managers import UserManager


def validate_birth_date(value):
    if value > timezone.localdate():
        raise ValidationError("Birth date cannot be in the future.")


class User(AbstractUser):
    username = None
    email = models.EmailField("email address", unique=True)
    zip_code = models.CharField(max_length=10)
    birth_date = models.DateField(validators=[validate_birth_date])
    timezone = models.CharField(max_length=63, default="UTC")
    email_notifications = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["zip_code", "birth_date"]

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="accounts_user_email_ci_unique"),
        ]

    def __str__(self):
        return self.email


class SavedEvent(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="saved_events",
    )
    event_id = models.CharField(max_length=100)
    label = models.CharField(max_length=200, blank=True)
    title = models.CharField(max_length=200, blank=True)
    start_time_utc = models.DateTimeField(null=True, blank=True)
    end_time_utc = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=63, blank=True)
    location_label = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("owner", "event_id"),
                name="accounts_saved_event_owner_event_unique",
            ),
        ]

    def __str__(self):
        return self.label or self.event_id


class Location(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="locations",
    )
    label = models.CharField(max_length=120)
    latitude = models.DecimalField(max_digits=8, decimal_places=5)
    longitude = models.DecimalField(max_digits=8, decimal_places=5)
    elevation_meters = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    timezone = models.CharField(max_length=63, default="UTC")
    source = models.CharField(max_length=40, default="manual")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("label", "created_at")
        constraints = [
            models.UniqueConstraint(fields=("owner", "label"), name="accounts_location_owner_label_unique"),
        ]

    def clean(self):
        super().clean()
        if not -90 <= float(self.latitude) <= 90:
            raise ValidationError("Latitude must be between -90 and 90 degrees.")
        if not -180 <= float(self.longitude) <= 180:
            raise ValidationError("Longitude must be between -180 and 180 degrees.")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, TypeError):
            raise ValidationError("Use an IANA timezone, such as America/Los_Angeles.")

    def __str__(self):
        return self.label
