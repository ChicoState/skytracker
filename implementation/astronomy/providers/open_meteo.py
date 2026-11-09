import json
import math
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ..models import ProviderError


GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


def fetch_json(url):
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "SkyTracker"})
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise ProviderError("open_meteo", "REQUEST_FAILED", "Location lookup was unavailable") from exc
    if not isinstance(payload, dict):
        raise ProviderError("open_meteo", "INVALID_RESPONSE", "Location lookup returned unexpected data")
    return payload


def geocode_zip(zip_code):
    query = urlencode({"postalcode": zip_code, "countrycode": "US", "count": 1, "language": "en", "format": "json"})
    payload = fetch_json(f"{GEOCODING_URL}?{query}")
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        raise ProviderError("open_meteo", "LOCATION_NOT_FOUND", "No location was found for that ZIP code")
    result = results[0]
    try:
        latitude = float(result["latitude"])
        longitude = float(result["longitude"])
        label = str(result["name"])
        timezone = str(result.get("timezone") or "UTC")
    except (KeyError, TypeError, ValueError) as exc:
        raise ProviderError("open_meteo", "INVALID_RESPONSE", "Location lookup returned unexpected data") from exc
    if not all(math.isfinite(value) for value in (latitude, longitude)):
        raise ProviderError("open_meteo", "INVALID_RESPONSE", "Location lookup returned invalid coordinates")
    return type("ResolvedLocation", (), {
        "label": label,
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone,
    })()
