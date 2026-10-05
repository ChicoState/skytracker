from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

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
