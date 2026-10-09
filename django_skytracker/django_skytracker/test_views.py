from datetime import datetime, timezone
from unittest.mock import patch

from django.test import SimpleTestCase

from implementation.sky_demo import DemoError


class HomePageTests(SimpleTestCase):
    # The first visit should show the search form without calling an API.
    @patch("django_skytracker.views.get_sky_report")
    def test_home_shows_search_form(self, get_sky_report):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="city"')
        get_sky_report.assert_not_called()

    # A search should display the constellation names returned by the API layer.
    @patch("django_skytracker.views.get_sky_report")
    def test_search_shows_constellations(self, get_sky_report):
        get_sky_report.return_value = {
            "label": "Chico, California, United States",
            "latitude": 39.73,
            "longitude": -121.84,
            "instant": datetime(2026, 10, 7, tzinfo=timezone.utc),
            "visible": [("Cygnus", 48.2), ("Orion", 12.4)],
            "constellation_count": 89,
            "moon_events": [("01:30", "Rise")],
        }
        response = self.client.get("/", {"city": "Chico, CA"})
        self.assertContains(response, "Cygnus")
        self.assertContains(response, "Orion")
        self.assertContains(response, 'data-constellation-filters')
        self.assertContains(response, 'visible-constellations-data')
        self.assertContains(response, "01:30 Rise")
        get_sky_report.assert_called_once_with("Chico, CA")

    # Empty and oversized searches should never reach the API layer.
    @patch("django_skytracker.views.get_sky_report")
    def test_invalid_search_stays_local(self, get_sky_report):
        self.assertContains(self.client.get("/", {"city": " "}), "Enter a city")
        self.assertContains(self.client.get("/", {"city": "x" * 121}), "under 120 characters")
        get_sky_report.assert_not_called()

    # An upstream failure should become a readable page message.
    @patch("django_skytracker.views.get_sky_report", side_effect=DemoError("Location not found"))
    def test_api_error_is_displayed(self, get_sky_report):
        response = self.client.get("/", {"city": "Unknownville"})
        self.assertContains(response, "Location not found")
        get_sky_report.assert_called_once_with("Unknownville")
