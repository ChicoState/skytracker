import unittest
from unittest.mock import patch

from implementation.astronomy.models import ProviderError
from implementation.astronomy.providers.open_meteo import geocode_zip


class OpenMeteoTests(unittest.TestCase):
    def test_geocode_zip_returns_normalized_location(self):
        payload = {
            "results": [
                {
                    "name": "Seattle",
                    "latitude": 47.6062,
                    "longitude": -122.3321,
                    "timezone": "America/Los_Angeles",
                }
            ]
        }
        with patch(
            "implementation.astronomy.providers.open_meteo.fetch_json",
            return_value=payload,
        ):
            location = geocode_zip("98101")

        self.assertEqual(location.label, "Seattle")
        self.assertEqual(location.latitude, 47.6062)
        self.assertEqual(location.longitude, -122.3321)
        self.assertEqual(location.timezone, "America/Los_Angeles")

    def test_geocode_zip_rejects_missing_results(self):
        with patch(
            "implementation.astronomy.providers.open_meteo.fetch_json",
            return_value={"results": []},
        ):
            with self.assertRaises(ProviderError) as error:
                geocode_zip("98101")

        self.assertEqual(error.exception.code, "LOCATION_NOT_FOUND")

