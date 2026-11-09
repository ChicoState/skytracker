from datetime import date, timedelta

from .models import ProviderError
from .providers.astronomy_engine import fetch_planet_events
from .providers.meteor_showers import fetch_meteor_shower_events
from .providers.usno import fetch_daily_events


def get_events_for_location(location, start_date, end_date, event_types=None, include_extended=False):
    if end_date < start_date:
        raise ValueError("end_date must not be before start_date")
    if (end_date - start_date).days > 31:
        raise ValueError("Event ranges cannot exceed 32 days")

    allowed_types = set(event_types or [])
    events = []
    errors = []
    day = start_date
    while day <= end_date:
        try:
            daily_events = fetch_daily_events(location, day)
            events.extend(
                event for event in daily_events
                if not allowed_types or event.event_type in allowed_types
            )
        except ProviderError as exc:
            errors.append(exc)
        day += timedelta(days=1)
    if include_extended:
        if not allowed_types or any(event_type.value.startswith("PLANET_") for event_type in allowed_types):
            try:
                planet_events = fetch_planet_events(location, start_date, end_date)
                events.extend(
                    event for event in planet_events
                    if not allowed_types or event.event_type in allowed_types
                )
            except ProviderError as exc:
                errors.append(exc)
        if not allowed_types or any(event_type.value == "METEOR_SHOWER" for event_type in allowed_types):
            meteor_events, meteor_errors = fetch_meteor_shower_events(location, start_date, end_date)
            events.extend(
                event for event in meteor_events
                if not allowed_types or event.event_type in allowed_types
            )
            errors.extend(meteor_errors)
    return sorted(events, key=lambda event: event.start_time_utc), errors
