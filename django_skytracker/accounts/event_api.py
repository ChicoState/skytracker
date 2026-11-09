from datetime import date, datetime, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.http import JsonResponse

from implementation.astronomy.event_service import get_events_for_location
from implementation.astronomy.models import EventType, ProviderError
from implementation.astronomy.providers.open_meteo import geocode_zip

from .models import Location, SavedEvent


def _error(status, code, message):
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


def _date(value, default):
    if not value:
        return default
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError("Dates must use YYYY-MM-DD format.")


def _location(request):
    location_id = request.GET.get("location_id", "").strip()
    if location_id:
        if not location_id.isdigit():
            raise LookupError
        location = Location.objects.filter(owner=request.user, pk=location_id).first()
        if not location:
            raise LookupError
        return location
    resolved = geocode_zip(request.user.zip_code)
    return SimpleNamespace(
        label=resolved.label,
        latitude=resolved.latitude,
        longitude=resolved.longitude,
        timezone=request.user.timezone,
    )


def _event_types(request):
    values = request.GET.getlist("type") or request.GET.get("types", "").split(",")
    values = [value.strip().upper() for value in values if value.strip()]
    try:
        return [EventType(value) for value in values]
    except ValueError:
        raise ValueError("Unknown event type.")


def _serialize(event, timezone, saved_ids):
    local_start = event.start_time_utc.astimezone(timezone)
    local_peak = event.peak_time_utc.astimezone(timezone) if event.peak_time_utc else None
    local_end = event.end_time_utc.astimezone(timezone) if event.end_time_utc else None
    return {
        "id": event.external_id,
        "eventType": event.event_type.value,
        "title": event.title,
        "startTimeUtc": event.start_time_utc.isoformat(),
        "startTimeLocal": local_start.isoformat(),
        "peakTimeUtc": event.peak_time_utc.isoformat() if event.peak_time_utc else None,
        "peakTimeLocal": local_peak.isoformat() if local_peak else None,
        "endTimeUtc": event.end_time_utc.isoformat() if event.end_time_utc else None,
        "endTimeLocal": local_end.isoformat() if local_end else None,
        "visibilityStatus": event.visibility_status.value,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "source": event.source,
        "description": event.description,
        "isSaved": event.external_id in saved_ids,
    }


def events_api(request):
    if not request.user.is_authenticated:
        return _error(401, "AUTHENTICATION_REQUIRED", "Sign in to request personal sky events.")
    try:
        user_timezone = ZoneInfo(request.user.timezone)
        start = _date(request.GET.get("start"), datetime.now(user_timezone).date())
        end = _date(request.GET.get("end"), start + timedelta(days=30))
        event_types = _event_types(request)
        location = _location(request)
        timezone = ZoneInfo(location.timezone)
        events, provider_errors = get_events_for_location(
            location, start, end, event_types, include_extended=True
        )
    except (ValueError, ZoneInfoNotFoundError) as exc:
        return _error(422, "VALIDATION_ERROR", str(exc))
    except LookupError:
        return _error(404, "LOCATION_NOT_FOUND", "That location is not available.")
    except ProviderError as exc:
        return _error(503, exc.code, exc.message)

    saved_ids = set(
        SavedEvent.objects.filter(owner=request.user, event_id__in=[event.external_id for event in events])
        .values_list("event_id", flat=True)
    )
    return JsonResponse({
        "location": {
            "label": location.label,
            "latitude": float(location.latitude),
            "longitude": float(location.longitude),
            "timezone": location.timezone,
        },
        "start": start.isoformat(),
        "end": end.isoformat(),
        "data": [_serialize(event, timezone, saved_ids) for event in events],
        "errors": [{"provider": error.provider, "code": error.code, "message": error.message} for error in provider_errors],
    })
