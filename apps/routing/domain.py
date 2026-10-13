"""Domain models for routing and geocoding."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Coordinates:
    """Geographic point coordinate."""

    lat: float
    lng: float
    label: str | None = None


@dataclass(frozen=True)
class RoutePoint:
    """Point along a route geometry with cumulative distance and duration."""

    lat: float
    lng: float
    cumulative_distance_miles: float
    cumulative_duration_seconds: float


@dataclass
class RawRoute:
    """Route option returned by a routing provider."""

    id: str
    name: str
    distance_miles: float
    duration_minutes: float
    geometry: str  # Encoded polyline string
    coordinates: list[tuple[float, float]] = field(default_factory=list)  # [(lat, lng), ...]
    route_points: list[RoutePoint] = field(default_factory=list)


@dataclass(frozen=True)
class SampledCheckpoint:
    """Interpolated checkpoint along a route before weather data is attached."""

    mile: float
    lat: float
    lng: float
    cumulative_duration_seconds: float
    eta: datetime


@dataclass(frozen=True)
class GeocodingResult:
    """Geocoded location result."""

    label: str
    lat: float
    lng: float
