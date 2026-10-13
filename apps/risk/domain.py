"""Domain models and data structures for the risk engine.

Pure Python domain representations without framework or database dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class RiskLevel(IntEnum):
    """Ordered risk levels where higher integer indicates higher risk."""

    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        labels = {
            RiskLevel.LOW: "Low",
            RiskLevel.MODERATE: "Moderate",
            RiskLevel.HIGH: "High",
            RiskLevel.SEVERE: "Severe",
            RiskLevel.NO_TRAVEL: "No Travel",
        }
        return labels[self]


@dataclass(frozen=True)
class CheckpointWeather:
    """Weather measurements at a specific checkpoint and ETA."""

    wind_mph: float
    rain_in_per_hr: float
    snow_in_per_hr: float
    wind_gust_mph: float | None = None
    temperature_f: float | None = None


@dataclass(frozen=True)
class Checkpoint:
    """A sampled checkpoint along a route."""

    mile: float
    lat: float
    lng: float
    eta: str  # ISO 8601 string
    weather: CheckpointWeather
    condition_levels: dict[str, int]  # {"wind": 0..4, "rain": 0..4, "snow": 0..4}
    risk: RiskLevel
    reason: str
    segment_miles: float = 0.0  # Road length this checkpoint represents


@dataclass(frozen=True)
class RouteSummary:
    """Aggregated risk and travel metrics for a single route."""

    severe_miles: float
    high_miles: float
    no_travel_miles: float
    average_risk: float
    total_distance_miles: float
    total_duration_minutes: float
    worst_checkpoint: Checkpoint | None = None

    @property
    def is_blocked(self) -> bool:
        """True if the route encounters any No Travel conditions."""
        return self.no_travel_miles > 0


@dataclass
class RouteAnalysis:
    """Complete analysis for a single route option."""

    id: str
    name: str
    distance_miles: float
    duration_minutes: float
    geometry: str  # Encoded polyline or GeoJSON coordinates string
    summary: RouteSummary
    checkpoints: list[Checkpoint] = field(default_factory=list)


@dataclass(frozen=True)
class RouteRecommendation:
    """Outcome of lexicographic ranking across all route options."""

    recommended_route_id: str
    recommendation_reason: str
    ranked_route_ids: list[str]
    all_routes_blocked: bool = False
    details: dict[str, Any] = field(default_factory=dict)
