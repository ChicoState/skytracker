# Small, network-free checks for the standalone API demonstration.

import unittest

from sky_demo import (
    DemoError,
    altitude_degrees,
    parse_nasa_eclipse_catalog,
    parse_iau_meteor_showers,
    parse_aurora_forecast,
    parse_visible_planets,
    moon_rise_set,
    parse_at,
    parse_coordinates,
    parse_lmst,
    visible_constellations,
)


class SkyDemoTests(unittest.TestCase):
    def test_aurora_forecast_uses_nearest_grid_point(self):
        payload = {
            "coordinates": [
                [0, 65, 10],
                [1, 65, 80],
                [359, 65, 20],
            ],
            "Observation Time": "2026-11-07T04:48:00Z",
            "Forecast Time": "2026-11-07T05:46:00Z",
        }
        result = parse_aurora_forecast(payload, 65, 0.9)
        self.assertEqual(result["probability"], 80)
        self.assertEqual(result["latitude"], 65)
        self.assertEqual(result["longitude"], 1)

    def test_visible_planets_are_sorted_by_altitude(self):
        payload = {
            "data": [
                {"name": "Mars", "altitude": 12.5, "azimuth": 180, "magnitude": 1.2},
                {"name": "Venus", "altitude": 48.0, "azimuth": 90, "magnitude": -3.5},
            ]
        }
        self.assertEqual(
            [planet["name"] for planet in parse_visible_planets(payload)],
            ["Venus", "Mars"],
        )

    def test_nasa_eclipse_catalog_parses_solar_and_lunar_rows(self):
        source = """
        <table><tr><td>09708</td><td>2026 Mar 03</td><td>11:34:52</td>
        <td>75</td><td>323</td><td>133</td><td>T</td></tr></table>
        """
        self.assertEqual(
            parse_nasa_eclipse_catalog(source, "lunar"),
            [{"date": "2026-03-03", "time_utc": "11:34:52", "type": "total", "category": "lunar"}],
        )

    def test_iau_meteor_showers_parse_established_annual_records(self):
        payload = {
            "data": [{
                "Code": "PER",
                "Name": "Perseids",
                "solution": [{
                    "activity": "annual",
                    "LoSb": 139.0,
                    "LoSe": 145.0,
                    "Ra": 48.0,
                    "De": 58.0,
                    "Vg": 59.0,
                    "Parent body": "109P/Swift-Tuttle",
                }],
            }]
        }
        self.assertEqual(parse_iau_meteor_showers(payload)[0]["code"], "PER")

    def test_coordinate_pair_and_bounds(self):
        self.assertEqual(parse_coordinates("39.7285,-121.8375"), (39.7285, -121.8375))
        with self.assertRaises(DemoError):
            parse_coordinates("91,0")

    def test_timestamp_needs_explicit_time_zone(self):
        self.assertEqual(
            parse_at("2026-10-07T05:00:00Z").isoformat(),
            "2026-10-07T05:00:00+00:00",
        )
        with self.assertRaises(DemoError):
            parse_at("2026-10-07T05:00:00")

    def test_altitude_at_zenith_and_opposite_point(self):
        self.assertAlmostEqual(altitude_degrees(0, 0, 0, 0), 90)
        self.assertAlmostEqual(altitude_degrees(0, 0, 180, 0), -90)

    def test_sidereal_response_and_catalog_filter(self):
        payload = {"properties": {"data": [{"lmst": "00:00:00.0000"}]}}
        lmst = parse_lmst(payload)
        catalog = {
            "features": [
                {"properties": {"name": "Above"}, "geometry": {"type": "Point", "coordinates": [0, 0]}},
                {"properties": {"name": "Below"}, "geometry": {"type": "Point", "coordinates": [180, 0]}},
            ]
        }
        self.assertEqual([name for name, _ in visible_constellations(catalog, 0, lmst)], ["Above"])

    def test_moon_events_include_only_rise_and_set(self):
        payload = {
            "properties": {
                "data": {
                    "moondata": [
                        {"phen": "Rise", "time": "10:57"},
                        {"phen": "Upper Transit", "time": "17:41"},
                        {"phen": "Set", "time": "23:12"},
                    ]
                }
            }
        }
        self.assertEqual(moon_rise_set(payload), [("10:57", "Rise"), ("23:12", "Set")])

    def test_moon_events_keep_multiple_rises_on_one_date(self):
        payload = {
            "properties": {
                "data": {
                    "moondata": [
                        {"phen": "Rise", "time": "00:05"},
                        {"phen": "Rise", "time": "23:55"},
                    ]
                }
            }
        }
        self.assertEqual(moon_rise_set(payload), [("00:05", "Rise"), ("23:55", "Rise")])

    def test_moon_event_rejects_impossible_time(self):
        payload = {"properties": {"data": {"moondata": [{"phen": "Rise", "time": "99:99"}]}}}
        with self.assertRaises(DemoError):
            moon_rise_set(payload)


if __name__ == "__main__":
    unittest.main()
