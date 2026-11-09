from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from accounts.models import Location, SavedEvent, User
from implementation.astronomy.models import AstronomyEvent, EventType


class EventApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="sky@example.com",
            password="A-strong-password-123",
            zip_code="98101",
            birth_date=date(2000, 5, 12),
            timezone="America/Los_Angeles",
        )
        self.client.force_login(self.user)

    def test_events_api_uses_profile_zip_and_returns_local_time(self):
        event = AstronomyEvent(
            external_id="sunrise:2026-10-19:47.6062:-122.3321:rise",
            event_type=EventType.SUNRISE,
            title="Sunrise",
            start_time_utc=datetime(2026, 10, 19, 14, 12, tzinfo=timezone.utc),
            latitude=47.6062,
            longitude=-122.3321,
            source="usno",
        )
        with patch(
            "accounts.event_api.geocode_zip",
            return_value=SimpleNamespace(
                label="Seattle",
                latitude=47.6062,
                longitude=-122.3321,
                timezone="America/Los_Angeles",
            ),
        ), patch(
            "accounts.event_api.get_events_for_location",
            return_value=([event], []),
        ):
            response = self.client.get(
                reverse("events_api"),
                {"start": "2026-10-19", "end": "2026-10-19"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["location"]["label"], "Seattle")
        self.assertEqual(body["data"][0]["eventType"], "SUNRISE")
        self.assertEqual(body["data"][0]["startTimeLocal"], "2026-10-19T07:12:00-07:00")

    def test_events_api_rejects_a_location_owned_by_another_user(self):
        other = User.objects.create_user(
            email="other@example.com",
            password="A-strong-password-123",
            zip_code="80202",
            birth_date=date(2000, 5, 12),
        )
        location = Location.objects.create(
            owner=other,
            label="Private",
            latitude=39.7,
            longitude=-104.9,
            timezone="America/Denver",
        )

        response = self.client.get(reverse("events_api"), {"location_id": location.pk})

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "LOCATION_NOT_FOUND")

    def test_saved_event_keeps_calendar_timing(self):
        response = self.client.post(
            reverse("accounts:saved_events"),
            {
                "event_id": "sunrise:2026-10-19:47.6062:-122.3321:rise",
                "label": "Sunrise",
                "start_time_utc": "2026-10-19T14:12:00+00:00",
                "timezone": "America/Los_Angeles",
                "location_label": "Seattle",
            },
        )

        self.assertEqual(response.status_code, 302)
        saved = SavedEvent.objects.get(owner=self.user)
        self.assertEqual(saved.title, "Sunrise")
        self.assertEqual(saved.timezone, "America/Los_Angeles")
        self.assertEqual(saved.start_time_utc.isoformat(), "2026-10-19T14:12:00+00:00")

