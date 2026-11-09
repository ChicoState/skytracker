from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError

from .models import Location, SavedEvent, User


class AccountDetailsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "zip_code",
            "birth_date",
            "timezone",
            "email_notifications",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        existing_users = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            existing_users = existing_users.exclude(pk=self.instance.pk)
        if existing_users.exists():
            raise ValidationError("An account already uses this email address.")
        return email

    def clean_timezone(self):
        timezone = self.cleaned_data["timezone"]
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            raise ValidationError("Use an IANA timezone, such as America/Los_Angeles.")
        return timezone


class SignupForm(AccountDetailsForm):
    password1 = forms.CharField(label="Password", strip=False, widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", strip=False, widget=forms.PasswordInput)

    def clean_password2(self):
        password2 = self.cleaned_data["password2"]
        if self.cleaned_data.get("password1") != password2:
            raise ValidationError("The two passwords do not match.")
        return password2

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password2")
        if password:
            password_validation.validate_password(password, self.instance)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class PasswordResetForm(forms.Form):
    email = forms.EmailField(label="Account email")
    new_password1 = forms.CharField(label="New password", strip=False, widget=forms.PasswordInput)
    new_password2 = forms.CharField(label="Confirm new password", strip=False, widget=forms.PasswordInput)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        try:
            self.user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise ValidationError("No account was found with that email address.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("new_password1")
        password2 = cleaned_data.get("new_password2")
        if password1 and password1 != password2:
            self.add_error("new_password2", "The two passwords do not match.")
        if password1 and hasattr(self, "user"):
            password_validation.validate_password(password1, self.user)
        return cleaned_data

    def save(self):
        self.user.set_password(self.cleaned_data["new_password1"])
        self.user.save(update_fields=["password"])
        return self.user


class SavedEventForm(forms.ModelForm):
    class Meta:
        model = SavedEvent
        fields = ("event_id", "label")

    def clean_event_id(self):
        return self.cleaned_data["event_id"].strip()


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ("label", "latitude", "longitude", "elevation_meters", "timezone")
        widgets = {
            "latitude": forms.NumberInput(attrs={"step": "0.00001", "min": "-90", "max": "90"}),
            "longitude": forms.NumberInput(attrs={"step": "0.00001", "min": "-180", "max": "180"}),
            "elevation_meters": forms.NumberInput(attrs={"step": "0.01"}),
        }

    def clean_timezone(self):
        timezone = self.cleaned_data["timezone"]
        try:
            ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            raise ValidationError("Use an IANA timezone, such as America/Los_Angeles.")
        return timezone


class AdminUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email",)


class AdminUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"
