from datetime import timedelta, timezone

import astronomy

from ..models import AstronomyEvent, EventType, ProviderError, VisibilityStatus


PLANETS = ("Mercury", "Venus", "Mars", "Jupiter", "Saturn")


def _event_time(value):
    result = value.Utc()
    if result.tzinfo is None:
        return result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def fetch_planet_events(location, start_date, end_date, planets=PLANETS):
    try:
        observer = astronomy.Observer(
            float(location.latitude),
            float(location.longitude),
            float(getattr(location, "elevation_meters", 0) or 0),
        )
        events = []
        day = start_date
        while day <= end_date:
            start = astronomy.Time.Parse(f"{day.isoformat()}T00:00:00Z")
            for planet_name in planets:
                body = getattr(astronomy.Body, planet_name)
                for direction, event_type, suffix in (
                    (astronomy.Direction.Rise, EventType.PLANET_RISE, "rise"),
                    (astronomy.Direction.Set, EventType.PLANET_SET, "set"),
                ):
                    value = astronomy.SearchRiseSet(body, observer, direction, start, 1.0)
                    if value is None:
                        continue
                    timestamp = _event_time(value)
                    if timestamp.date() != day:
                        continue
                    events.append(
                        AstronomyEvent(
                            external_id=f"planet-{suffix}:{planet_name.lower()}:{timestamp.isoformat()}:{location.latitude}:{location.longitude}",
                            event_type=event_type,
                            title=f"{planet_name} {'rises' if suffix == 'rise' else 'sets'}",
                            start_time_utc=timestamp,
                            visibility_status=VisibilityStatus.UNKNOWN,
                            latitude=float(location.latitude),
                            longitude=float(location.longitude),
                            source="astronomy_engine",
                            source_version="2.1.19",
                            description="Planet rise/set time calculated for this location; daylight and cloud conditions are not included.",
                        )
                    )
            day += timedelta(days=1)
        return events
    except (AttributeError, TypeError, ValueError, OverflowError) as exc:
        raise ProviderError("astronomy_engine", "CALCULATION_FAILED", "Planet events could not be calculated") from exc

