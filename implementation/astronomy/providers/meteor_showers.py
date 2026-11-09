import json
from datetime import date, datetime, time, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..models import AstronomyEvent, EventType, ProviderError, VisibilityStatus


METEOR_SHOWER_URL = "https://meteorshowercal.com/api/v1"


def fetch_json(url):
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "SkyTracker/1.0"})
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise ProviderError("meteor_shower_cal", "REQUEST_FAILED", "Meteor shower data was unavailable") from exc
    if not isinstance(payload, dict):
        raise ProviderError("meteor_shower_cal", "INVALID_RESPONSE", "Meteor shower data was unexpected")
    return payload


def _parse_time(value, fallback):
    if not value:
        return fallback
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ProviderError("meteor_shower_cal", "INVALID_RESPONSE", "Meteor shower time was invalid") from exc
    if parsed.tzinfo is None:
        raise ProviderError("meteor_shower_cal", "INVALID_RESPONSE", "Meteor shower time had no timezone")
    return parsed.astimezone(timezone.utc)


def fetch_meteor_shower_event(location, day):
    query = urlencode({"lat": float(location.latitude), "lon": float(location.longitude), "date": day.isoformat()})
    payload = fetch_json(f"{METEOR_SHOWER_URL}/tonight?{query}")
    shower = payload.get("shower")
    if not isinstance(shower, dict) or not shower.get("name"):
        return None
    fallback_start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    fallback_end = fallback_start + timedelta(days=1)
    best_window = payload.get("bestWindow") or {}
    if not isinstance(best_window, dict):
        raise ProviderError("meteor_shower_cal", "INVALID_RESPONSE", "Meteor shower window was unexpected")
    start = _parse_time(best_window.get("start"), fallback_start)
    end = _parse_time(best_window.get("end"), fallback_end)
    if end <= start:
        raise ProviderError("meteor_shower_cal", "INVALID_RESPONSE", "Meteor shower window was invalid")
    code = str(shower.get("code") or shower.get("slug") or "unknown").lower()
    description = "Best local observing window; meteor rates are estimates and weather can change."
    if payload.get("cloudPct") is not None:
        description += f" Forecast cloud cover: {payload['cloudPct']}%."
    metadata = payload.get("meta")
    source_version = metadata.get("version", "v1") if isinstance(metadata, dict) else "v1"
    return AstronomyEvent(
        external_id=f"meteor-shower:{code}:{day.isoformat()}:{location.latitude}:{location.longitude}",
        event_type=EventType.METEOR_SHOWER,
        title=f"{shower['name']} best viewing",
        start_time_utc=start,
        end_time_utc=end,
        visibility_status=VisibilityStatus.UNKNOWN,
        latitude=float(location.latitude),
        longitude=float(location.longitude),
        source="meteor_shower_cal",
        source_version=str(source_version),
        description=description,
    )


def fetch_meteor_shower_events(location, start_date, end_date):
    events = []
    errors = []
    day = start_date
    while day <= end_date:
        try:
            event = fetch_meteor_shower_event(location, day)
            if event:
                events.append(event)
        except ProviderError as exc:
            errors.append(exc)
        day += timedelta(days=1)
    return events, errors
