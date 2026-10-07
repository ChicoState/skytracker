#!/usr/bin/env python3
# Show approximate constellations and Moon rise/set for one Earth location.

import argparse
from datetime import datetime, timezone
import json
import math
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
SIDEREAL_URL = "https://aa.usno.navy.mil/api/siderealtime"
MOON_URL = "https://aa.usno.navy.mil/api/rstt/oneday"
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


# Read command-line input, fetch the API data, and print the sky report.
def main():
    parser = argparse.ArgumentParser(
        description="Fetch approximate above-horizon constellations and Moon rise/set for a location. No API key needed."
    )
    parser.add_argument("location", help='Place name ("Chico, CA") or latitude,longitude ("39.7285,-121.8375")')
    parser.add_argument("--at", help="ISO 8601 instant with offset, e.g. 2026-10-07T05:00:00Z; defaults to now UTC")
    args = parser.parse_args()

    try:
        instant = parse_at(args.at)
        latitude, longitude, label = resolve_location(args.location)
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
    except DemoError as exc:
        parser.exit(2, f"error: {exc}\n")

    print(f"Location: {label} ({latitude:.4f}, {longitude:.4f})")
    print(f"Sky at: {instant:%Y-%m-%d %H:%M:%S} UTC")
    print(f"Constellation reference points above horizon: {len(visible)} of {len(catalog['features'])}")
    for name, altitude in visible:
        print(f"  {name}: {altitude:.1f}°")
    print(f"Moon rise/set on {day} (UT1, approximately UTC):")
    for clock, event in moon_events:
        print(f"  {clock} {event}")
    present_events = {event for _, event in moon_events}
    for event in ("Rise", "Set"):
        if event not in present_events:
            print(f"  {event}: no event on this date")
    print("Sources: Open-Meteo (place names), USNO (sidereal time and Moon events), d3-celestial via GitHub (constellation points).")
    print("Note: Constellation points are approximate; daylight, weather, obstructions, and constellation edges are not checked.")


if __name__ == "__main__":
    main()
