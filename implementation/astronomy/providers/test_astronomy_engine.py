import unittest
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from implementation.astronomy.models import EventType
from implementation.astronomy.providers.astronomy_engine import fetch_planet_events


class AstronomyEngineTests(unittest.TestCase):
    def test_planet_rise_and_set_are_normalized(self):
        class FakeTime:
            def Utc(self):
                return datetime(2026, 10, 19, 2, 0, tzinfo=timezone.utc)

        fake_astronomy = SimpleNamespace(
            Body=SimpleNamespace(Venus="Venus"),
            Direction=SimpleNamespace(Rise="rise", Set="set"),
            Observer=lambda latitude, longitude, elevation: (latitude, longitude, elevation),
            Time=SimpleNamespace(Parse=lambda value: value),
            SearchRiseSet=lambda body, observer, direction, start, limit: FakeTime(),
        )
        location = SimpleNamespace(latitude=47.6062, longitude=-122.3321, elevation_meters=0)
        with patch("implementation.astronomy.providers.astronomy_engine.astronomy", fake_astronomy):
            events = fetch_planet_events(location, date(2026, 10, 19), date(2026, 10, 19), planets=("Venus",))

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].event_type, EventType.PLANET_RISE)
        self.assertEqual(events[0].title, "Venus rises")
        self.assertEqual(events[1].event_type, EventType.PLANET_SET)
