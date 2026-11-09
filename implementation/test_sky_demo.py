# Small, network-free checks for the standalone API demonstration.

import unittest

from implementation.sky_demo import (
    DemoError,
    altitude_degrees,
    moon_rise_set,
    parse_at,
    parse_coordinates,
    parse_lmst,
    visible_constellations,
)


class SkyDemoTests(unittest.TestCase):
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
