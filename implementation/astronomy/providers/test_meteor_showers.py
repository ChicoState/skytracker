import unittest
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

from implementation.astronomy.models import EventType
from implementation.astronomy.providers.meteor_showers import fetch_meteor_shower_event


class MeteorShowerTests(unittest.TestCase):
    def test_best_window_becomes_a_timed_local_shower_event(self):
        payload = {
            "meta": {"version": "v1"},
            "shower": {"code": "PER", "name": "Perseids"},
            "bestWindow": {
                "start": "2026-08-13T03:00:00-07:00",
                "end": "2026-08-13T05:00:00-07:00",
            },
            "cloudPct": 12,
        }
        location = SimpleNamespace(latitude=47.6062, longitude=-122.3321)
        with patch(
            "implementation.astronomy.providers.meteor_showers.fetch_json",
            return_value=payload,
        ):
            event = fetch_meteor_shower_event(location, date(2026, 8, 13))

        self.assertEqual(event.event_type, EventType.METEOR_SHOWER)
        self.assertEqual(event.title, "Perseids best viewing")
        self.assertEqual(event.start_time_utc.hour, 10)
        self.assertEqual(event.end_time_utc.hour, 12)
        self.assertIn("12%", event.description)

