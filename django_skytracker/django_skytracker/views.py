from datetime import date, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from django.shortcuts import render

from implementation.astronomy.event_service import get_events_for_location
from implementation.sky_demo import DemoError, get_sky_report

from accounts.models import Location, SavedEvent


# Show the search form and fetch a sky report when a location is submitted.
def home(request):
    city = request.GET.get("city", "").strip()
    selected_location_id = request.GET.get("location_id", "").strip()
    context = {"city": city, "locations": [], "selected_location_id": selected_location_id}
    if request.user.is_authenticated:
        context["locations"] = Location.objects.filter(owner=request.user)

    if "city" in request.GET or selected_location_id:
        event_location = None
        report_location = city
        if selected_location_id:
            if not request.user.is_authenticated or not selected_location_id.isdigit():
                context["error"] = "Choose one of your saved locations."
                return render(request, "sky.html", context)
            event_location = Location.objects.filter(owner=request.user, pk=selected_location_id).first()
            if not event_location:
                context["error"] = "That saved location was not found."
                return render(request, "sky.html", context)
            report_location = f"{event_location.latitude},{event_location.longitude}"
        if not city:
            if not selected_location_id:
                context["error"] = "Enter a city or latitude,longitude coordinates."
        elif len(city) > 120:
            context["error"] = "Keep the location under 120 characters."
        if not context.get("error"):
            try:
                report = get_sky_report(report_location)
                context["report"] = report
                # Keep this UI adapter separate from the data-collection layer,
                # which returns (name, altitude) tuples for the server-rendered list.
                context["filterable_constellations"] = [
                    {"id": name, "name": name, "altitude": altitude}
                    for name, altitude in report["visible"]
                ]
                if event_location is None:
                    event_location = SimpleNamespace(
                        label=report["label"],
                        latitude=report["latitude"],
                        longitude=report["longitude"],
                        timezone=request.user.timezone if request.user.is_authenticated else "UTC",
                    )
                start_date = _event_start_date(request.GET.get("start"))
                end_date = start_date + timedelta(days=30)
                events, provider_errors = get_events_for_location(
                    event_location,
                    start_date,
                    end_date,
                    include_extended=request.user.is_authenticated,
                )
                saved_ids = set()
                if request.user.is_authenticated:
                    saved_ids = set(
                        SavedEvent.objects.filter(
                            owner=request.user,
                            event_id__in=[event.external_id for event in events],
                        ).values_list("event_id", flat=True)
                    )
                timezone = ZoneInfo(event_location.timezone)
                context["event_start"] = start_date
                context["event_end"] = end_date
                context["event_location"] = event_location
                context["event_errors"] = provider_errors
                context["events"] = [
                    {
                        "event": event,
                        "local_start": event.start_time_utc.astimezone(timezone),
                        "is_saved": event.external_id in saved_ids,
                    }
                    for event in events
                ]
            except DemoError as exc:
                context["error"] = str(exc)
            except ValueError as exc:
                context["error"] = str(exc)
    return render(request, "sky.html", context)


def _event_start_date(value):
    if not value:
        return date.today()
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Start date must use YYYY-MM-DD format.") from exc


def filters_preview(request):
    return render(request, "skytracker/filters_preview.html")
