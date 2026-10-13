"""Weather provider interfacing with Open-Meteo forecast API."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Protocol

import httpx
from django.conf import settings
from django.core.cache import cache

from apps.weather.domain import HourlyForecastPoint

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 1800  # 30 minutes
BATCH_CHUNK_SIZE = 40


class WeatherProvider(Protocol):
    """Protocol for weather data providers."""

    def get_forecasts_for_points(
        self,
        coordinates: list[tuple[float, float]],
        forecast_days: int = 3,
    ) -> list[HourlyForecastPoint]: ...


class OpenMeteoProvider:
    """Open-Meteo client supporting batched coordinate forecasting."""

    def __init__(self, base_url: str | None = None, timeout_seconds: float = 12.0):
        self.base_url = (
            base_url or getattr(settings, "OPEN_METEO_BASE_URL", "https://api.open-meteo.com/v1")
        ).rstrip("/")
        self.timeout = timeout_seconds

    def get_forecasts_for_points(
        self,
        coordinates: list[tuple[float, float]],
        forecast_days: int = 3,
    ) -> list[HourlyForecastPoint]:
        """Fetch hourly forecasts for multiple coordinates with caching and batching."""
        if not coordinates:
            return []

        results: list[HourlyForecastPoint | None] = [None] * len(coordinates)
        uncached_indices: list[int] = []

        # Check cache for rounded coordinates
        for idx, (lat, lng) in enumerate(coordinates):
            cache_key = f"weather:{round(lat, 2):.2f}:{round(lng, 2):.2f}:{forecast_days}"
            cached: HourlyForecastPoint | None = cache.get(cache_key)
            if cached is not None:
                results[idx] = cached
            else:
                uncached_indices.append(idx)

        # Batch fetch uncached coordinates in chunks
        if uncached_indices:
            for i in range(0, len(uncached_indices), BATCH_CHUNK_SIZE):
                chunk_indices = uncached_indices[i : i + BATCH_CHUNK_SIZE]
                chunk_coords = [coordinates[ci] for ci in chunk_indices]

                try:
                    fetched_forecasts = self._fetch_open_meteo_chunk(chunk_coords, forecast_days)
                    for ci, forecast in zip(chunk_indices, fetched_forecasts, strict=False):
                        results[ci] = forecast
                        cache_key = (
                            f"weather:{round(forecast.lat, 2):.2f}:"
                            f"{round(forecast.lng, 2):.2f}:{forecast_days}"
                        )
                        cache.set(cache_key, forecast, timeout=CACHE_TTL_SECONDS)
                except Exception as e:
                    logger.warning("Open-Meteo batch request failed (%s), generating fallback", e)
                    for ci in chunk_indices:
                        lat, lng = coordinates[ci]
                        fallback = self._generate_fallback_forecast(lat, lng, forecast_days)
                        results[ci] = fallback

        # Replace any remaining None with fallback
        final_results: list[HourlyForecastPoint] = []
        for idx, res in enumerate(results):
            if res is not None:
                final_results.append(res)
            else:
                lat, lng = coordinates[idx]
                final_results.append(self._generate_fallback_forecast(lat, lng, forecast_days))

        return final_results

    def _fetch_open_meteo_chunk(
        self,
        coords: list[tuple[float, float]],
        forecast_days: int,
    ) -> list[HourlyForecastPoint]:
        url = f"{self.base_url}/forecast"
        latitudes = ",".join(f"{c[0]:.4f}" for c in coords)
        longitudes = ",".join(f"{c[1]:.4f}" for c in coords)

        params = {
            "latitude": latitudes,
            "longitude": longitudes,
            "hourly": "wind_speed_10m,precipitation,rain,snowfall,wind_gusts_10m,temperature_2m",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "temperature_unit": "fahrenheit",
            "timezone": "UTC",
            "forecast_days": max(1, min(16, forecast_days)),
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        # When querying multiple coordinates, Open-Meteo returns a list of JSON objects;
        # when querying a single coordinate, it returns a single JSON object.
        items: list[dict[str, Any]] = data if isinstance(data, list) else [data]

        forecasts: list[HourlyForecastPoint] = []
        for idx, item in enumerate(items):
            hourly = item.get("hourly", {})
            times = hourly.get("time", [])

            timestamps = [
                datetime.fromisoformat(t).replace(tzinfo=UTC)
                if "Z" not in t and "+" not in t
                else datetime.fromisoformat(t.replace("Z", "+00:00"))
                for t in times
            ]

            lat = float(item.get("latitude", coords[idx][0]))
            lng = float(item.get("longitude", coords[idx][1]))

            rain = hourly.get("rain", hourly.get("precipitation", [0.0] * len(times)))
            snow = hourly.get("snowfall", [0.0] * len(times))
            wind = hourly.get("wind_speed_10m", [0.0] * len(times))
            gusts = hourly.get("wind_gusts_10m", [0.0] * len(times))
            temp = hourly.get("temperature_2m", [55.0] * len(times))

            forecasts.append(
                HourlyForecastPoint(
                    lat=lat,
                    lng=lng,
                    timestamps=timestamps,
                    wind_speed_mph=[float(w or 0.0) for w in wind],
                    rain_in_per_hr=[float(r or 0.0) for r in rain],
                    snow_in_per_hr=[float(s or 0.0) for s in snow],
                    wind_gusts_mph=[float(g or 0.0) for g in gusts],
                    temperature_f=[float(t or 0.0) for t in temp],
                )
            )

        return forecasts

    def _generate_fallback_forecast(
        self, lat: float, lng: float, forecast_days: int
    ) -> HourlyForecastPoint:
        """Simulate realistic hourly weather series when API is offline."""
        now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
        total_hours = forecast_days * 24

        timestamps = [now + timedelta(hours=h) for h in range(total_hours)]
        # Synthetic moderate winds
        wind = [12.0 + (h % 8) * 1.5 for h in range(total_hours)]
        rain = [0.0] * total_hours
        snow = [0.0] * total_hours

        return HourlyForecastPoint(
            lat=lat,
            lng=lng,
            timestamps=timestamps,
            wind_speed_mph=wind,
            rain_in_per_hr=rain,
            snow_in_per_hr=snow,
            wind_gusts_mph=[w * 1.3 for w in wind],
            temperature_f=[50.0] * total_hours,
        )
