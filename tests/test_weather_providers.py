"""Unit tests for Open-Meteo weather provider and WeatherService."""

from datetime import UTC, datetime

import pytest
import respx
from django.core.cache import cache
from httpx import Response

from apps.routing.domain import SampledCheckpoint
from apps.weather.providers import OpenMeteoProvider
from apps.weather.service import WeatherService


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


def _make_mock_open_meteo_response(lat: float, lng: float, num_hours: int = 72):
    times = []
    base_time = datetime(2026, 10, 14, 0, 0, tzinfo=UTC)
    for h in range(num_hours):
        t = datetime.fromtimestamp(base_time.timestamp() + h * 3600, tz=UTC)
        times.append(t.strftime("%Y-%m-%dT%H:00"))

    # Pattern: wind starts at 15 mph and increases
    wind = [15.0 + (h % 30) for h in range(num_hours)]
    rain = [0.0 if h % 5 != 0 else 0.4 for h in range(num_hours)]
    snow = [0.0] * num_hours
    gusts = [w * 1.25 for w in wind]
    temp = [60.0] * num_hours

    return {
        "latitude": lat,
        "longitude": lng,
        "hourly": {
            "time": times,
            "wind_speed_10m": wind,
            "rain": rain,
            "snowfall": snow,
            "wind_gusts_10m": gusts,
            "temperature_2m": temp,
        },
    }


class TestOpenMeteoProvider:
    @respx.mock
    def test_get_forecasts_single_point(self):
        mock_data = _make_mock_open_meteo_response(41.88, -87.63)
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=Response(200, json=mock_data)
        )

        provider = OpenMeteoProvider()
        forecasts = provider.get_forecasts_for_points([(41.88, -87.63)], forecast_days=3)

        assert len(forecasts) == 1
        f = forecasts[0]
        assert f.lat == pytest.approx(41.88)
        assert f.lng == pytest.approx(-87.63)
        assert len(f.timestamps) == 72
        assert f.wind_speed_mph[0] == 15.0

    @respx.mock
    def test_get_forecasts_multiple_points_batched(self):
        # Open-Meteo returns a list of objects when multiple coordinates are queried
        mock_list = [
            _make_mock_open_meteo_response(41.88, -87.63),
            _make_mock_open_meteo_response(41.70, -89.50),
        ]
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=Response(200, json=mock_list)
        )

        provider = OpenMeteoProvider()
        coords = [(41.88, -87.63), (41.70, -89.50)]
        forecasts = provider.get_forecasts_for_points(coords, forecast_days=3)

        assert len(forecasts) == 2
        assert forecasts[0].lat == pytest.approx(41.88)
        assert forecasts[1].lat == pytest.approx(41.70)

    @respx.mock
    def test_caching_avoids_repeated_calls(self):
        mock_data = _make_mock_open_meteo_response(41.88, -87.63)
        weather_mock = respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=Response(200, json=mock_data)
        )

        provider = OpenMeteoProvider()
        coords = [(41.88, -87.63)]

        provider.get_forecasts_for_points(coords, forecast_days=3)
        provider.get_forecasts_for_points(coords, forecast_days=3)

        assert weather_mock.call_count == 1

    @respx.mock
    def test_error_fallback(self):
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=Response(500, json={"error": "Down"})
        )

        provider = OpenMeteoProvider()
        forecasts = provider.get_forecasts_for_points([(41.88, -87.63)], forecast_days=3)

        assert len(forecasts) == 1
        assert len(forecasts[0].timestamps) == 72
        assert forecasts[0].wind_speed_mph[0] >= 0.0


class TestWeatherService:
    @respx.mock
    def test_enrich_checkpoints_closest_hour_eta(self):
        mock_data = _make_mock_open_meteo_response(41.88, -87.63, num_hours=72)
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=Response(200, json=mock_data)
        )

        service = WeatherService(provider=OpenMeteoProvider())

        # Checkpoint ETA at 14:35 (should match hour 15)
        eta = datetime(2026, 10, 14, 14, 35, tzinfo=UTC)
        checkpoints = [
            SampledCheckpoint(
                mile=0.0,
                lat=41.88,
                lng=-87.63,
                cumulative_duration_seconds=0.0,
                eta=eta,
            )
        ]

        readings = service.get_weather_for_checkpoints(checkpoints)

        assert len(readings) == 1
        # Hour 15 should match
        expected_wind = mock_data["hourly"]["wind_speed_10m"][15]
        assert readings[0].wind_mph == expected_wind

    @respx.mock
    def test_corridor_heatmap_matrix_dimensions(self):
        mock_list = [
            _make_mock_open_meteo_response(41.88, -87.63),
            _make_mock_open_meteo_response(41.70, -89.50),
            _make_mock_open_meteo_response(41.50, -91.00),
        ]
        respx.get("https://api.open-meteo.com/v1/forecast").mock(
            return_value=Response(200, json=mock_list)
        )

        service = WeatherService(provider=OpenMeteoProvider())
        corridor_coords = [(41.88, -87.63), (41.70, -89.50), (41.50, -91.00)]
        start_time = datetime(2026, 10, 14, 6, 0, tzinfo=UTC)

        matrix = service.get_corridor_heatmap_matrix(
            corridor_coords, start_time=start_time, load_weight_lb=42_000, hours=48
        )

        assert len(matrix.points) == 3
        assert len(matrix.risk_matrix) == 48
        assert len(matrix.wind_matrix) == 48
        assert len(matrix.risk_matrix[0]) == 3
        # Ensure risks are within 0..4
        for row in matrix.risk_matrix:
            for val in row:
                assert 0 <= val <= 4
