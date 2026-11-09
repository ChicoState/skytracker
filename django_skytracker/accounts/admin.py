from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import AdminUserChangeForm, AdminUserCreationForm
from .models import Location, SavedEvent, User


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("label", "owner", "latitude", "longitude", "timezone", "updated_at")
    list_filter = ("timezone", "source")
    search_fields = ("label", "owner__email")


@admin.register(SavedEvent)
class SavedEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "label", "owner", "created_at")
    list_filter = ("created_at",)
    search_fields = ("event_id", "label", "owner__email")


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    form = AdminUserChangeForm
    add_form = AdminUserCreationForm
    model = User
    list_display = ("email", "first_name", "last_name", "is_staff")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "zip_code", "birth_date", "timezone", "email_notifications")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "zip_code", "birth_date", "password1", "password2"),
            },
        ),
    )
    search_fields = ("email", "first_name", "last_name")
