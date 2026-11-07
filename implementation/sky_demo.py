#!/usr/bin/env python3
# Show approximate constellations and Moon rise/set for one Earth location.

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import re
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
SIDEREAL_URL = "https://aa.usno.navy.mil/api/siderealtime"
MOON_URL = "https://aa.usno.navy.mil/api/rstt/oneday"
PLANETS_URL = "https://api.visibleplanets.dev/v3"
NASA_SOLAR_ECLIPSES_URL = "https://eclipse.gsfc.nasa.gov/SEcat5/SE2001-2100.html"
NASA_LUNAR_ECLIPSES_URL = "https://eclipse.gsfc.nasa.gov/LEcat5/LE2001-2100.html"
IAU_METEOR_SHOWERS_URL = "https://iaumdc.astro.sk/downloads/lists_shw_data/streamestablisheddata.json"
NOAA_AURORA_URL = "https://services.swpc.noaa.gov/json/ovation_aurora_latest.json"
# Pin the data revision so a future catalog edit cannot silently change this demo.
CATALOG_URL = (
    "https://api.github.com/repos/ofrohn/d3-celestial/contents/"
    "data/constellations.json?ref=b56735c22935b7bde41a944a74e0f780ca0c6dfa"
)


# Use this error for failures that should be shown directly to the user.
class DemoError(Exception):
    pass


# Request one API URL and return its JSON, with a readable error on failure.
def fetch_json(url, source, accept="application/json"):
    request = Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": "SkyTracker-standalone-demo",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:
            data = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise DemoError(f"Could not read {source}: {exc}") from exc
    if not isinstance(data, dict) or ("error" in data and data["error"]):
        raise DemoError(f"{source} returned an error or unexpected response")
    return data


def fetch_text(url, source, accept="text/plain"):
    request = Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": "SkyTracker-standalone-demo",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:
            return response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeError) as exc:
        raise DemoError(f"Could not read {source}: {exc}") from exc


# Parse a decimal latitude,longitude pair and reject invalid ranges.
def parse_coordinates(value):
    try:
        parts = value.split(",")
        if len(parts) != 2:
            raise ValueError
        latitude, longitude = (float(part.strip()) for part in parts)
    except ValueError as exc:
        raise DemoError("Coordinates must be latitude,longitude in decimal degrees") from exc
    if not (math.isfinite(latitude) and -90 <= latitude <= 90):
        raise DemoError("Latitude must be between -90 and 90 degrees")
    if not (math.isfinite(longitude) and -180 <= longitude <= 180):
        raise DemoError("Longitude must be between -180 and 180 degrees")
    return latitude, longitude


# Use entered coordinates directly or look up a place name with Open-Meteo.
def resolve_location(value):
    parts = value.split(",")
    if len(parts) == 2:
        try:
            float(parts[0].strip())
            float(parts[1].strip())
        except ValueError:
            pass  # A place name such as "Chico, CA" goes to the geocoder.
        else:
            lat, lon = parse_coordinates(value)
            return lat, lon, "Entered coordinates"

    query = urlencode({"name": value, "count": 1, "language": "en", "format": "json"})
    data = fetch_json(f"{GEOCODE_URL}?{query}", "Open-Meteo geocoding")
    results = data.get("results")
    if not isinstance(results, list) or not results:
        raise DemoError(f"No location found for {value!r}; try a city and region or coordinates")
    place = results[0]
    try:
        lat, lon = parse_coordinates(f"{place['latitude']},{place['longitude']}")
        label = ", ".join(
            str(place[key]) for key in ("name", "admin1", "country") if place.get(key)
        )
    except (KeyError, TypeError) as exc:
        raise DemoError("Open-Meteo returned an unexpected location") from exc
    return lat, lon, label


# Convert the requested time to UTC, or use the current UTC time.
def parse_at(value):
    if value is None:
        instant = datetime.now(timezone.utc)
    else:
        try:
            instant = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise DemoError("--at must be an ISO 8601 timestamp with a time zone") from exc
        if instant.tzinfo is None:
            raise DemoError("--at needs an explicit time zone, for example ...T05:00:00Z")
    instant = instant.astimezone(timezone.utc).replace(microsecond=0)
    if not 1800 <= instant.year <= 2050:
        raise DemoError("USNO sidereal data supports years 1800 through 2050")
    return instant


# Read local mean sidereal time from the USNO response and return degrees.
def parse_lmst(payload):
    try:
        clock = payload["properties"]["data"][0]["lmst"]
        hours, minutes, seconds = clock.split(":")
        hours, minutes, seconds = int(hours), int(minutes), float(seconds)
        if not (0 <= hours < 24 and 0 <= minutes < 60 and 0 <= seconds < 60):
            raise ValueError
    except (KeyError, IndexError, AttributeError, TypeError, ValueError) as exc:
        raise DemoError("USNO returned unexpected sidereal time data") from exc
    return 15 * (hours + minutes / 60 + seconds / 3600)


# Calculate a sky point's geometric altitude above or below the horizon.
def altitude_degrees(latitude, declination, right_ascension, sidereal_degrees):
    lat = math.radians(latitude)
    dec = math.radians(declination)
    hour_angle = math.radians(sidereal_degrees - right_ascension)
    sine = math.sin(lat) * math.sin(dec) + math.cos(lat) * math.cos(dec) * math.cos(hour_angle)
    return math.degrees(math.asin(max(-1.0, min(1.0, sine))))


# List catalog label points above the observer's horizon, highest first.
def visible_constellations(payload, latitude, sidereal_degrees):
    features = payload.get("features")
    if not isinstance(features, list) or not features:
        raise DemoError("Constellation catalog is missing expected reference points")
    visible = []
    for feature in features:
        try:
            name = feature["properties"]["name"]
            geometry = feature["geometry"]
            right_ascension, declination = geometry["coordinates"]
            if geometry["type"] != "Point" or not isinstance(name, str):
                raise ValueError
            if not all(math.isfinite(value) for value in (right_ascension, declination)):
                raise ValueError
            altitude = altitude_degrees(latitude, declination, right_ascension, sidereal_degrees)
        except (KeyError, TypeError, ValueError) as exc:
            raise DemoError("Constellation catalog has an unexpected point") from exc
        if altitude > 0:
            visible.append((name, altitude))
    return sorted(visible, key=lambda item: (-item[1], item[0]))


# Keep every Moon rise and set in the USNO response in time order.
def moon_rise_set(payload):
    try:
        entries = payload["properties"]["data"]["moondata"]
    except (KeyError, TypeError) as exc:
        raise DemoError("USNO returned unexpected Moon event data") from exc
    if not isinstance(entries, list):
        raise DemoError("USNO returned unexpected Moon event data")
    events = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise DemoError("USNO returned unexpected Moon event data")
        phenomenon, clock = entry.get("phen"), entry.get("time")
        if phenomenon in ("Rise", "Set") and clock not in (None, "null"):
            if not isinstance(clock, str) or not re.fullmatch(r"\d{2}:\d{2}", clock):
                raise DemoError("USNO returned an unexpected Moon event time")
            hours, minutes = (int(part) for part in clock.split(":"))
            if not (0 <= hours < 24 and 0 <= minutes < 60):
                raise DemoError("USNO returned an unexpected Moon event time")
            events.append((clock, phenomenon))
    return sorted(events)


def parse_visible_planets(payload):
    entries = payload.get("data")
    if not isinstance(entries, list):
        raise DemoError("Visible Planets API returned unexpected planetary data")
    planets = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise DemoError("Visible Planets API returned unexpected planetary data")
        try:
            planet = {
                "name": str(entry["name"]),
                "altitude": float(entry["altitude"]),
                "azimuth": float(entry["azimuth"]),
                "magnitude": float(entry["magnitude"]),
            }
        except (KeyError, TypeError, ValueError) as exc:
            raise DemoError("Visible Planets API returned an unexpected body") from exc
        if not all(math.isfinite(planet[key]) for key in ("altitude", "azimuth", "magnitude")):
            raise DemoError("Visible Planets API returned an unexpected body")
        planet["constellation"] = entry.get("constellation", "")
        planets.append(planet)
    return sorted(planets, key=lambda item: (-item["altitude"], item["name"]))


class _HTMLRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.cell_rows = []
        self.text = []
        self._cells = []
        self._cell_text = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._cells = []
        elif tag in ("td", "th"):
            self._cell_text = []

    def handle_data(self, data):
        self.text.append(data)
        if self._cell_text is not None:
            self._cell_text.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell_text is not None:
            self._cells.append(" ".join("".join(self._cell_text).split()))
            self._cell_text = None
        elif tag == "tr" and self._cells:
            self.rows.append(" ".join(self._cells))
            self.cell_rows.append(self._cells[:])
            self._cells = []


def parse_nasa_eclipse_catalog(source, category):
    parser = _HTMLRows()
    parser.feed(source)
    month_names = "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
    pattern = re.compile(
        rf"\b(20\d{{2}})\s+({month_names})\s+(\d{{1,2}})\s+"
        r"(\d{2}:\d{2}:\d{2})\s+\d+\s+\d+\s+\d+\s+([A-Za-z]{1,2})\b"
    )
    eclipses = []
    type_names = {"P": "partial", "A": "annular", "An": "annular", "T": "total", "H": "hybrid", "N": "penumbral"}
    catalog_text = " ".join(" ".join(parser.text).split())
    for match in pattern.finditer(catalog_text):
        if match.group(5) not in type_names:
            continue
        year, month, day, time_utc, eclipse_type = match.groups()
        date = datetime.strptime(f"{year} {month} {day}", "%Y %b %d").date().isoformat()
        eclipses.append({"date": date, "time_utc": time_utc, "type": type_names[eclipse_type], "category": category})
    if not eclipses:
        raise DemoError("NASA returned no parseable eclipse catalog entries")
    return sorted(eclipses, key=lambda item: item["date"])


def parse_iau_meteor_showers(payload):
    entries = payload.get("data")
    if not isinstance(entries, list):
        raise DemoError("IAU MDC returned unexpected meteor-shower data")
    showers = []
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("Code") or not entry.get("Name"):
            continue
        solutions = entry.get("solution")
        if not isinstance(solutions, list) or not solutions:
            continue
        solution = solutions[0]
        if not isinstance(solution, dict) or solution.get("activity") != "annual":
            continue
        showers.append({
            "code": str(entry["Code"]),
            "name": str(entry["Name"]),
            "activity_start_solar_longitude": solution.get("LoSb"),
            "activity_end_solar_longitude": solution.get("LoSe"),
            "radiant_ra": solution.get("Ra"),
            "radiant_dec": solution.get("De"),
            "velocity_km_s": solution.get("Vg"),
            "parent_body": solution.get("Parent body", ""),
        })
    if not showers:
        raise DemoError("IAU MDC returned no established annual meteor showers")
    return sorted(showers, key=lambda item: item["name"])


def parse_aurora_forecast(payload, latitude, longitude):
    coordinates = payload.get("coordinates")
    if not isinstance(coordinates, list) or not coordinates:
        raise DemoError("NOAA returned unexpected aurora forecast data")
    nearest = None
    for row in coordinates:
        if not isinstance(row, list) or len(row) < 3:
            continue
        try:
            grid_longitude, grid_latitude, probability = (float(value) for value in row[:3])
        except (TypeError, ValueError):
            continue
        if not (
            math.isfinite(grid_longitude)
            and math.isfinite(grid_latitude)
            and math.isfinite(probability)
            and 0 <= grid_longitude <= 360
            and -90 <= grid_latitude <= 90
            and 0 <= probability <= 100
        ):
            continue
        longitude_distance = abs(((grid_longitude - longitude + 180) % 360) - 180)
        distance = math.hypot(grid_latitude - latitude, longitude_distance)
        if nearest is None or distance < nearest[0]:
            nearest = (distance, grid_longitude, grid_latitude, probability)
    if nearest is None:
        raise DemoError("NOAA returned no valid aurora forecast coordinates")
    _, grid_longitude, grid_latitude, probability = nearest
    if grid_longitude > 180:
        grid_longitude -= 360
    return {
        "probability": round(probability),
        "latitude": round(grid_latitude, 1),
        "longitude": round(grid_longitude, 1),
        "observation_time": payload.get("Observation Time", ""),
        "forecast_time": payload.get("Forecast Time", ""),
    }


# Fetch the sky data once so both the terminal demo and website use the same result.
def get_sky_report(location, at=None):
    instant = parse_at(at)
    latitude, longitude, label = resolve_location(location)
    coordinates = f"{latitude},{longitude}"
    day = instant.strftime("%Y-%m-%d")
    sidereal_query = urlencode(
        {
            "date": day,
            "time": instant.strftime("%H:%M:%S"),
            "coords": coordinates,
            "reps": 1,
            "intv_mag": 1,
            "intv_unit": "seconds",
        }
    )
    moon_query = urlencode({"date": day, "coords": coordinates, "tz": 0})
    sidereal = parse_lmst(fetch_json(f"{SIDEREAL_URL}?{sidereal_query}", "USNO sidereal time"))
    moon_events = moon_rise_set(fetch_json(f"{MOON_URL}?{moon_query}", "USNO Moon events"))
    catalog = fetch_json(CATALOG_URL, "GitHub constellation catalog", "application/vnd.github.raw+json")
    visible = visible_constellations(catalog, latitude, sidereal)
    planet_query = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "time": instant.isoformat().replace("+00:00", "Z"),
            "aboveHorizon": "true",
        }
    )
    planets = parse_visible_planets(
        fetch_json(f"{PLANETS_URL}?{planet_query}", "Visible Planets API")
    )
    solar_eclipses = parse_nasa_eclipse_catalog(
        fetch_text(NASA_SOLAR_ECLIPSES_URL, "NASA solar eclipse catalog"), "solar"
    )
    lunar_eclipses = parse_nasa_eclipse_catalog(
        fetch_text(NASA_LUNAR_ECLIPSES_URL, "NASA lunar eclipse catalog"), "lunar"
    )
    eclipses = [eclipse for eclipse in solar_eclipses + lunar_eclipses if eclipse["date"] >= day]
    eclipses.sort(key=lambda item: (item["date"], item["time_utc"]))
    meteor_showers = parse_iau_meteor_showers(
        fetch_json(IAU_METEOR_SHOWERS_URL, "IAU MDC meteor-shower catalog")
    )
    aurora = parse_aurora_forecast(
        fetch_json(NOAA_AURORA_URL, "NOAA aurora forecast"), latitude, longitude
    )
    return {
        "label": label,
        "latitude": latitude,
        "longitude": longitude,
        "instant": instant,
        "visible": visible,
        "constellation_count": len(catalog["features"]),
        "moon_events": moon_events,
        "planets": planets,
        "eclipses": eclipses,
        "meteor_showers": meteor_showers,
        "aurora": aurora,
    }


# Read command-line input, fetch the sky report, and print it.
def main():
    parser = argparse.ArgumentParser(
        description="Fetch approximate above-horizon constellations and Moon rise/set for a location. No API key needed."
    )
    parser.add_argument("location", help='Place name ("Chico, CA") or latitude,longitude ("39.7285,-121.8375")')
    parser.add_argument("--at", help="ISO 8601 instant with offset, e.g. 2026-10-07T05:00:00Z; defaults to now UTC")
    args = parser.parse_args()

    try:
        report = get_sky_report(args.location, args.at)
    except DemoError as exc:
        parser.exit(2, f"error: {exc}\n")

    print(f"Location: {report['label']} ({report['latitude']:.4f}, {report['longitude']:.4f})")
    print(f"Sky at: {report['instant']:%Y-%m-%d %H:%M:%S} UTC")
    print(f"Constellation reference points above horizon: {len(report['visible'])} of {report['constellation_count']}")
    for name, altitude in report["visible"]:
        print(f"  {name}: {altitude:.1f}°")
    print(f"Moon rise/set on {report['instant']:%Y-%m-%d} (UT1, approximately UTC):")
    for clock, event in report["moon_events"]:
        print(f"  {clock} {event}")
    present_events = {event for _, event in report["moon_events"]}
    for event in ("Rise", "Set"):
        if event not in present_events:
            print(f"  {event}: no event on this date")
    print("Visible planets:")
    for planet in report["planets"]:
        print(f"  {planet['name']}: {planet['altitude']:.1f}° altitude, {planet['azimuth']:.1f}° azimuth, magnitude {planet['magnitude']:.1f}")
    print("Upcoming eclipses (times in UTC):")
    for eclipse in report["eclipses"][:10]:
        print(f"  {eclipse['date']} {eclipse['time_utc']}: {eclipse['type']} {eclipse['category']}")
    print("Established annual meteor showers (IAU MDC):")
    for shower in report["meteor_showers"][:10]:
        print(f"  {shower['code']} {shower['name']}: radiant RA {shower['radiant_ra']}°, Dec {shower['radiant_dec']}°")
    aurora = report["aurora"]
    print(f"Aurora forecast near location: {aurora['probability']}% at {aurora['latitude']:.1f}°, {aurora['longitude']:.1f}°")
    print("Sources: Open-Meteo, USNO, d3-celestial via GitHub, Visible Planets API, and NASA eclipse catalogs.")
    print("Note: Constellation points are approximate; daylight, weather, obstructions, and constellation edges are not checked.")


if __name__ == "__main__":
    main()
