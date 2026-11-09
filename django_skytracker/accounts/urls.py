from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import TemplateView

from .views import (
    PasswordResetView,
    SignupView,
    delete_saved_event,
    location_create,
    location_delete,
    location_edit,
    locations,
    profile,
    saved_events,
)

app_name = "accounts"

urlpatterns = [
    path("signup/", SignupView.as_view(), name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path(
        "password-reset/",
        PasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "reset/complete/",
        TemplateView.as_view(template_name="accounts/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("profile/", profile, name="profile"),
    path("saved-events/", saved_events, name="saved_events"),
    path("saved-events/<int:pk>/delete/", delete_saved_event, name="delete_saved_event"),
    path("locations/", locations, name="locations"),
    path("locations/add/", location_create, name="location_create"),
    path("locations/<int:pk>/edit/", location_edit, name="location_edit"),
    path("locations/<int:pk>/delete/", location_delete, name="location_delete"),
]
