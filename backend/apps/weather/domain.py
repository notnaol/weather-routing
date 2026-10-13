"""Domain models for weather forecasts and corridor matrices."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class HourlyForecastPoint:
    """Hourly forecast series for a specific coordinate."""

    lat: float
    lng: float
    timestamps: list[datetime]
    wind_speed_mph: list[float]
    rain_in_per_hr: list[float]
    snow_in_per_hr: list[float]
    wind_gusts_mph: list[float] = field(default_factory=list)
    temperature_f: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class CorridorHeatmapMatrix:
    """Compact matrix representation for 0-48h forecast scrubbing."""

    points: list[tuple[float, float]]  # [(lat, lng), ...]
    start_time_iso: str
    risk_matrix: list[list[int]]  # [hour_index 0..47][point_index] -> RiskLevel (0..4)
    wind_matrix: list[list[float]]  # [hour_index][point_index]
    rain_matrix: list[list[float]]  # [hour_index][point_index]
    snow_matrix: list[list[float]]  # [hour_index][point_index]
