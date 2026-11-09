from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_datetime
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from .forms import AccountDetailsForm, LocationForm, PasswordResetForm, SavedEventForm, SignupForm
from .models import Location, SavedEvent


class SignupView(FormView):
    form_class = SignupForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)


class PasswordResetView(FormView):
    form_class = PasswordResetForm
    template_name = "accounts/password_reset_form.html"
    success_url = reverse_lazy("accounts:password_reset_complete")

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


@login_required
def profile(request):
    if request.method == "POST":
        form = AccountDetailsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect("accounts:profile")
    else:
        form = AccountDetailsForm(instance=request.user)
    return render(request, "accounts/profile.html", {"form": form})


@login_required
def saved_events(request):
    if request.method == "POST":
        form = SavedEventForm(request.POST)
        if form.is_valid():
            SavedEvent.objects.update_or_create(
                owner=request.user,
                event_id=form.cleaned_data["event_id"],
                defaults={
                    "label": form.cleaned_data["label"],
                    "title": request.POST.get("title", form.cleaned_data["label"]),
                    "start_time_utc": parse_datetime(request.POST.get("start_time_utc", "")),
                    "end_time_utc": parse_datetime(request.POST.get("end_time_utc", "")),
                    "timezone": request.POST.get("timezone", ""),
                    "location_label": request.POST.get("location_label", ""),
                },
            )
            return redirect("accounts:saved_events")
    else:
        form = SavedEventForm()

    return render(
        request,
        "accounts/saved_events.html",
        {
            "form": form,
            "saved_events": SavedEvent.objects.filter(owner=request.user),
        },
    )


@login_required
def delete_saved_event(request, pk):
    if request.method == "POST":
        SavedEvent.objects.filter(pk=pk, owner=request.user).delete()
    return redirect("accounts:saved_events")


@login_required
def locations(request):
    return render(request, "accounts/locations.html", {"locations": Location.objects.filter(owner=request.user)})


@login_required
def location_create(request):
    form = LocationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        location = form.save(commit=False)
        location.owner = request.user
        location.full_clean()
        location.save()
        return redirect("accounts:locations")
    return render(request, "accounts/location_form.html", {"form": form, "title": "Add a location"})


@login_required
def location_edit(request, pk):
    location = get_object_or_404(Location, pk=pk, owner=request.user)
    form = LocationForm(request.POST or None, instance=location)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("accounts:locations")
    return render(request, "accounts/location_form.html", {"form": form, "title": "Edit location"})


@login_required
def location_delete(request, pk):
    if request.method == "POST":
        Location.objects.filter(pk=pk, owner=request.user).delete()
    return redirect("accounts:locations")
