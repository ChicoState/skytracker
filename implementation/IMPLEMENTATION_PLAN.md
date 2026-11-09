# SkyTracker standalone API demonstration plan

## Goal and fit with the project

Create a small command-line Python demonstration that accepts a location and reports (1) constellation reference points above that location's horizon at a chosen instant and (2) Moon rise/set events on the corresponding date. This proved live API retrieval before the Django site was connected. The standalone script has no Django or database dependency; the Django search page now imports its fetching and conversion logic.

The prior `initial_api_plan.md` explored NASA/JPL close approaches, but Earth approach distance cannot establish visibility from a person's location. `astronomy_events_api_catalog.md` calls out that distinction. Moon rise and set are frequent events calculated for the entered observer, so they fit this location-based demonstration.

## Scope and data contract

- One executable file, `sky_demo.py`, in this folder. Python standard library only, run from an isolated `implementation/.venv`.
- Required positional location: a place name such as `"Chico, CA"` or decimal coordinates such as `"39.7285,-121.8375"`. Show the resolved name and coordinates before results.
- Optional `--at` is an ISO 8601 timestamp with an explicit offset; default is the current UTC instant. Convert it to UTC for the API queries. Report Moon event times on that UTC/UT1 date, not guessed local civil times.
- Return every catalog **reference point** above the geometric horizon at that instant, sorted by altitude. The catalog has 89 points for the 88 IAU constellations because Serpens has two parts. A point above the horizon is an approximation of a constellation's presence in the sky; a constellation edge may be above the horizon even when its reference point is not. Weather, sunlight, obstructions, and boundary intersection are outside this prototype.
- Return every Moon **Rise** and **Set** event that the USNO response includes for that date. Some dates or polar locations may have no rise or set. Other astronomy event families are outside this demonstration.
- Fail with a short, nonzero-exit error on invalid input or an API/schema failure. No credentials, persistent output, or scheduler are needed.

## API choices

| Purpose | Source | Request/data used |
| --- | --- | --- |
| Resolve a place name | [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api) | `GET /v1/search?name=...&count=1&language=en&format=json`; use returned latitude/longitude. Coordinates skip this request. |
| Get sky rotation for the observer | [USNO sidereal time API](https://aa.usno.navy.mil/data/api.html#sidereal-time) | `GET /api/siderealtime` with date, time, coordinates, and one interval; use `properties.data[0].lmst`. The live API requires `reps=1&intv_mag=1&intv_unit=seconds` despite documentation calling the interval optional. |
| Get the selected frequent event | [USNO one-day Sun/Moon API](https://aa.usno.navy.mil/data/api.html#complete-sun-and-moon-data-for-one-day) | `GET /api/rstt/oneday` with date, coordinates, `tz=0`; use `properties.data.moondata` Rise/Set entries. |
| Get constellation positions | [d3-celestial constellation GeoJSON](https://github.com/ofrohn/d3-celestial/blob/master/data/readme.md) via [GitHub Contents API](https://docs.github.com/en/rest/repos/contents?apiVersion=2022-11-28) | Fetch `data/constellations.json` as raw JSON at pinned commit `b56735c22935b7bde41a944a74e0f780ca0c6dfa`; each point has a name, right ascension, and declination. Public data needs no API key. |

Use the [USNO altitude relation](https://aa.usno.navy.mil/faq/alt_az): local sidereal angle and catalog right ascension give the hour angle; hour angle, declination, and observer latitude give altitude. The catalog positions are J2000 label points, while the sidereal time is for the query date. This deliberately modest calculation is suitable for a prototype, but values close to the horizon should not be treated as precise visibility predictions. The [IAU defines constellations as bounded regions](https://www.iau.org/IAU/IAU/Astronomy-FAQs/Constellations.aspx), which this prototype does not fully intersect with the horizon.

## Tasks and acceptance checks

1. **Create isolated folder and CLI.** Add `sky_demo.py`, ignore `.venv` and Python caches within this folder, and create a local virtual environment without pip (the WSL Python lacks `ensurepip`; this standard-library demo installs no packages). Check: `--help` describes accepted input and time convention.
2. **Fetch and interpret live data.** Geocode names only when needed; fetch sidereal time, Moon events, and the complete constellation point catalog with timeouts and response validation. Check: both a place name and a coordinate pair produce identified coordinates and nonempty constellation results; a no-event Moon day does not crash.
3. **Verify the calculation and failures.** Add small tests for coordinate validation, timestamp validation, altitude geometry, and representative API payload interpretation, then run a live smoke check. Check: tests pass, invalid input exits nonzero, and the live output lists source and limitations.
4. **Review isolation.** Inspect the final diff and Git status. Check: only demo-related files were created or changed by this work; existing project files and user material remain untouched.

## Run after implementation

From the repository root, use the short WSL launcher. With no arguments, it asks for a location; it creates the isolated `.venv` on first use if needed.

```bash
./sky
./sky "Chico, CA"
./sky "39.7285,-121.8375" --at 2026-10-07T05:00:00Z
```

From PowerShell in this repository, use `wsl ./sky` with the same optional arguments. The direct commands below are still available for debugging and tests:

```bash
python3 -m venv --without-pip implementation/.venv
implementation/.venv/bin/python implementation/sky_demo.py "Chico, CA"
implementation/.venv/bin/python implementation/sky_demo.py "39.7285,-121.8375" --at 2026-10-07T05:00:00Z
implementation/.venv/bin/python -m unittest discover -s implementation -p 'test_*.py'
```

No human API key or setup is required beyond network access. The program reads only public APIs.

## Django web demonstration on Data-Collection

The existing `main` branch was merged into `Data-Collection` without changing `main`. The Django root route now renders a plain search form. A submitted city or coordinate pair calls `get_sky_report()` in `sky_demo.py`, so the CLI and site share the same API requests and altitude calculation. The page shows all above-horizon catalog points and Moon rise/set events. The view does not use the database.

The web changes are limited to the root URL, template directory, a new view and template, and a Dockerfile copy of `implementation/`. Run `docker compose up --build` from the repository root, then open `http://localhost:8000/`. Before the first run, create an ignored `.env` using `.env.example` as described in `README.Docker.md`. No API key is required.

## Verification completed

- [x] Isolated `.venv` created with `--without-pip`; it is ignored by `implementation/.gitignore`.
- [x] Seven network-free `unittest` checks passed, including coordinate and timestamp errors, altitude geometry, Moon event filtering, duplicate Moon events, and invalid event times.
- [x] Live `"Chico, CA"` and `"39.7285,-121.8375"` runs succeeded. Both resolved to the same coordinates and returned 37 of 89 constellation reference points at `2026-10-07T05:00:00Z`.
- [x] A live `2026-10-08T05:00:00Z` run reported both Moon events in time order: 00:12 Set and 12:06 Rise. The `2026-10-07` response omitted Set and the program reported that without failing.
- [x] The default no-`--at` command and `--help` succeeded; invalid coordinates and a timestamp without a time zone produced nonzero exits.
- [x] The short `./sky` launcher passed shell syntax checks, accepted a prompted location, and worked as `wsl ./sky "Chico, CA"` from PowerShell with live API output.
