"""Weather service for checkpoint enrichment and 48-hour corridor heatmap calculation."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta

from apps.risk.classifier import classify_checkpoint
from apps.risk.domain import CheckpointWeather
from apps.routing.domain import SampledCheckpoint
from apps.weather.domain import CorridorHeatmapMatrix
from apps.weather.providers import OpenMeteoProvider, WeatherProvider


class WeatherService:
    """Service providing weather interpolation for checkpoints and trip corridor heatmaps."""

    def __init__(self, provider: WeatherProvider | None = None):
        self.provider = provider or OpenMeteoProvider()

    def get_weather_for_checkpoints(
        self, checkpoints: list[SampledCheckpoint]
    ) -> list[CheckpointWeather]:
        """Fetch and interpolate weather readings for checkpoints at their calculated ETAs."""
        if not checkpoints:
            return []

        coords = [(cp.lat, cp.lng) for cp in checkpoints]

        # Calculate forecast horizon needed
        now = datetime.now(UTC)
        max_eta = max(
            cp.eta.astimezone(UTC) if cp.eta.tzinfo else cp.eta.replace(tzinfo=UTC)
            for cp in checkpoints
        )
        days_ahead = max(3, math.ceil((max_eta - now).total_seconds() / 86400.0) + 1)
        forecast_days = min(16, days_ahead)

        forecasts = self.provider.get_forecasts_for_points(coords, forecast_days=forecast_days)
        weather_readings: list[CheckpointWeather] = []

        for cp, forecast in zip(checkpoints, forecasts, strict=False):
            eta_utc = cp.eta.astimezone(UTC) if cp.eta.tzinfo else cp.eta.replace(tzinfo=UTC)

            # Match to nearest forecast hour
            if not forecast.timestamps:
                weather_readings.append(
                    CheckpointWeather(wind_mph=10.0, rain_in_per_hr=0.0, snow_in_per_hr=0.0)
                )
                continue

            best_idx = min(
                range(len(forecast.timestamps)),
                key=lambda i: abs((forecast.timestamps[i] - eta_utc).total_seconds()),
            )

            reading = CheckpointWeather(
                wind_mph=round(forecast.wind_speed_mph[best_idx], 1),
                rain_in_per_hr=round(forecast.rain_in_per_hr[best_idx], 2),
                snow_in_per_hr=round(forecast.snow_in_per_hr[best_idx], 2),
                wind_gust_mph=round(forecast.wind_gusts_mph[best_idx], 1)
                if forecast.wind_gusts_mph
                else None,
                temperature_f=round(forecast.temperature_f[best_idx], 1)
                if forecast.temperature_f
                else None,
            )
            weather_readings.append(reading)

        return weather_readings

    def get_corridor_heatmap_matrix(
        self,
        corridor_points: list[tuple[float, float]],
        start_time: datetime,
        load_weight_lb: float,
        hours: int = 48,
    ) -> CorridorHeatmapMatrix:
        """Compute the 0-48h weather risk matrix along all trip corridor points."""
        if not corridor_points:
            return CorridorHeatmapMatrix(
                points=[],
                start_time_iso=start_time.isoformat(),
                risk_matrix=[],
                wind_matrix=[],
                rain_matrix=[],
                snow_matrix=[],
            )

        start_utc = (
            start_time.astimezone(UTC) if start_time.tzinfo else start_time.replace(tzinfo=UTC)
        ).replace(minute=0, second=0, microsecond=0)

        forecast_days = max(3, math.ceil(hours / 24.0) + 1)
        forecasts = self.provider.get_forecasts_for_points(
            corridor_points, forecast_days=forecast_days
        )

        risk_matrix: list[list[int]] = []
        wind_matrix: list[list[float]] = []
        rain_matrix: list[list[float]] = []
        snow_matrix: list[list[float]] = []

        for h in range(hours):
            target_hour = start_utc + timedelta(hours=h)
            h_risks: list[int] = []
            h_winds: list[float] = []
            h_rains: list[float] = []
            h_snows: list[float] = []

            for forecast in forecasts:
                if not forecast.timestamps:
                    h_risks.append(0)
                    h_winds.append(0.0)
                    h_rains.append(0.0)
                    h_snows.append(0.0)
                    continue

                best_idx = min(
                    range(len(forecast.timestamps)),
                    key=lambda i: abs((forecast.timestamps[i] - target_hour).total_seconds()),
                )

                w_speed = forecast.wind_speed_mph[best_idx]
                r_rate = forecast.rain_in_per_hr[best_idx]
                s_rate = forecast.snow_in_per_hr[best_idx]

                weather = CheckpointWeather(
                    wind_mph=w_speed,
                    rain_in_per_hr=r_rate,
                    snow_in_per_hr=s_rate,
                )
                risk_level, _, _ = classify_checkpoint(weather, load_weight_lb)

                h_risks.append(int(risk_level))
                h_winds.append(round(w_speed, 1))
                h_rains.append(round(r_rate, 2))
                h_snows.append(round(s_rate, 2))

            risk_matrix.append(h_risks)
            wind_matrix.append(h_winds)
            rain_matrix.append(h_rains)
            snow_matrix.append(h_snows)

        return CorridorHeatmapMatrix(
            points=corridor_points,
            start_time_iso=start_utc.isoformat(),
            risk_matrix=risk_matrix,
            wind_matrix=wind_matrix,
            rain_matrix=rain_matrix,
            snow_matrix=snow_matrix,
        )
