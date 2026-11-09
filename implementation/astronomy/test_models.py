import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from implementation.astronomy.event_service import get_events_for_location
from implementation.astronomy.models import EventType, ProviderError
from implementation.astronomy.providers.usno import parse_daily_events


class AstronomyEventTests(unittest.TestCase):
    def test_extended_events_combine_planets_and_meteor_showers(self):
        location = SimpleNamespace(latitude=39.7285, longitude=-121.8375, timezone="UTC", label="Home")
        planet_event = SimpleNamespace(event_type=EventType.PLANET_RISE, start_time_utc=datetime(2026, 10, 19, 1, tzinfo=timezone.utc))
        meteor_event = SimpleNamespace(event_type=EventType.METEOR_SHOWER, start_time_utc=datetime(2026, 10, 19, 2, tzinfo=timezone.utc))
        with patch("implementation.astronomy.event_service.fetch_daily_events", return_value=[]), patch(
            "implementation.astronomy.event_service.fetch_planet_events",
            return_value=[planet_event],
        ), patch(
            "implementation.astronomy.event_service.fetch_meteor_shower_events",
            return_value=([meteor_event], []),
        ):
            events, errors = get_events_for_location(
                location,
                date(2026, 10, 19),
                date(2026, 10, 19),
                include_extended=True,
            )

        self.assertEqual([event.event_type for event in events], [EventType.PLANET_RISE, EventType.METEOR_SHOWER])
        self.assertEqual(errors, [])

    def test_usno_daily_payload_becomes_normalized_events(self):
        payload = {
            "properties": {
                "data": {
                    "sundata": [
                        {"phen": "Begin Civil Twilight", "time": "06:01"},
                        {"phen": "Rise", "time": "07:12"},
                        {"phen": "Set", "time": "18:44"},
                        {"phen": "End Civil Twilight", "time": "19:55"},
                    ],
                    "moondata": [{"phen": "Rise", "time": "20:10"}],
                }
            }
        }

        events = parse_daily_events(payload, date(2026, 10, 19))

        self.assertEqual(
            [event.event_type for event in events],
            [
                EventType.TWILIGHT,
                EventType.SUNRISE,
                EventType.SUNSET,
                EventType.TWILIGHT,
                EventType.MOONRISE,
            ],
        )
        self.assertEqual(events[1].start_time_utc.hour, 7)

    def test_event_service_returns_partial_results_when_one_day_fails(self):
        location = SimpleNamespace(latitude=39.7285, longitude=-121.8375, timezone="UTC", label="Home")
        with patch("implementation.astronomy.event_service.fetch_daily_events", side_effect=[[], ProviderError("usno", "TIMEOUT", "timed out")]):
            events, errors = get_events_for_location(location, date(2026, 10, 19), date(2026, 10, 20))

        self.assertEqual(events, [])
        self.assertEqual(errors[0].provider, "usno")


if __name__ == "__main__":
    unittest.main()
