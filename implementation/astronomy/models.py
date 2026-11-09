from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class EventType(StrEnum):
    SUNRISE = "SUNRISE"
    SUNSET = "SUNSET"
    TWILIGHT = "TWILIGHT"
    MOONRISE = "MOONRISE"
    MOONSET = "MOONSET"
    PLANET_RISE = "PLANET_RISE"
    PLANET_SET = "PLANET_SET"
    METEOR_SHOWER = "METEOR_SHOWER"


class VisibilityStatus(StrEnum):
    VISIBLE = "VISIBLE"
    NOT_VISIBLE = "NOT_VISIBLE"
    UNKNOWN = "UNKNOWN"


class ProviderError(Exception):
    def __init__(self, provider, code, message):
        self.provider = provider
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class AstronomyEvent:
    external_id: str
    event_type: EventType
    title: str
    start_time_utc: datetime
    peak_time_utc: datetime | None = None
    end_time_utc: datetime | None = None
    visibility_status: VisibilityStatus = VisibilityStatus.UNKNOWN
    latitude: float | None = None
    longitude: float | None = None
    altitude_degrees: float | None = None
    azimuth_degrees: float | None = None
    source: str = ""
    source_version: str | None = None
    description: str = ""
