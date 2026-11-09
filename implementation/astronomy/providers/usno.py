import json
from datetime import date, datetime, time, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..models import AstronomyEvent, EventType, ProviderError, VisibilityStatus


USNO_RISE_SET_URL = "https://aa.usno.navy.mil/api/rstt/oneday"


def fetch_json(url):
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "SkyTracker"})
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise ProviderError("usno", "REQUEST_FAILED", "USNO was unavailable") from exc
    if not isinstance(payload, dict) or "properties" not in payload:
        raise ProviderError("usno", "INVALID_RESPONSE", "USNO returned an unexpected response")
    return payload


def fetch_daily_events(location, day):
    query = urlencode({"date": day.isoformat(), "coords": f"{location.latitude},{location.longitude}", "tz": 0})
    return parse_daily_events(fetch_json(f"{USNO_RISE_SET_URL}?{query}"), day)


def _utc_datetime(day, clock):
    try:
        parsed = datetime.combine(day, time.fromisoformat(clock))
    except (TypeError, ValueError) as exc:
        raise ProviderError("usno", "INVALID_RESPONSE", "USNO returned an invalid event time") from exc
    return parsed.replace(tzinfo=timezone.utc)


def _event(day, event_type, title, clock, location, suffix):
    timestamp = _utc_datetime(day, clock)
    external_id = f"{event_type.value.lower()}:{day.isoformat()}:{location.latitude}:{location.longitude}:{suffix}"
    return AstronomyEvent(
        external_id=external_id,
        event_type=event_type,
        title=title,
        start_time_utc=timestamp,
        visibility_status=VisibilityStatus.VISIBLE,
        latitude=float(location.latitude),
        longitude=float(location.longitude),
        source="usno",
        description="Event time supplied by the U.S. Naval Observatory; local observing conditions are not included.",
    )


def parse_daily_events(payload, day, location=None):
    try:
        data = payload["properties"]["data"]
        sun_entries = data.get("sundata", [])
        moon_entries = data.get("moondata", [])
    except (KeyError, TypeError) as exc:
        raise ProviderError("usno", "INVALID_RESPONSE", "USNO returned unexpected daily event data") from exc
    if not isinstance(sun_entries, list) or not isinstance(moon_entries, list):
        raise ProviderError("usno", "INVALID_RESPONSE", "USNO returned unexpected daily event data")
    location = location or type("Location", (), {"latitude": 0, "longitude": 0})()
    events = []
    sun_types = {
        "Rise": (EventType.SUNRISE, "Sunrise", "sunrise"),
        "Set": (EventType.SUNSET, "Sunset", "sunset"),
        "Begin Civil Twilight": (EventType.TWILIGHT, "Civil twilight begins", "civil-start"),
        "End Civil Twilight": (EventType.TWILIGHT, "Civil twilight ends", "civil-end"),
    }
    moon_types = {
        "Rise": (EventType.MOONRISE, "Moonrise", "moonrise"),
        "Set": (EventType.MOONSET, "Moonset", "moonset"),
    }
    for entry in sun_entries:
        if not isinstance(entry, dict) or entry.get("time") in (None, "null"):
            continue
        event_info = sun_types.get(entry.get("phen"))
        if event_info:
            events.append(_event(day, *event_info[:2], entry["time"], location, event_info[2]))
    for entry in moon_entries:
        if not isinstance(entry, dict) or entry.get("time") in (None, "null"):
            continue
        event_info = moon_types.get(entry.get("phen"))
        if event_info:
            events.append(_event(day, *event_info[:2], entry["time"], location, event_info[2]))
    return sorted(events, key=lambda event: event.start_time_utc)
