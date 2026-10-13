"""Unit tests for routing and geocoding providers with mocked HTTP endpoints."""

from datetime import UTC, datetime

import pytest
import respx
from django.core.cache import cache
from httpx import Response

from apps.routing.domain import Coordinates
from apps.routing.providers import OpenRouteServiceProvider
from apps.routing.service import RoutingService


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


MOCK_ORS_DIRECTIONS = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "summary": {
                    "distance": 160934.4,  # 100 miles in meters
                    "duration": 7200.0,  # 2 hours in seconds
                }
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-87.63, 41.88],
                    [-88.50, 41.80],
                    [-89.50, 41.70],
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "summary": {
                    "distance": 177027.8,  # 110 miles in meters
                    "duration": 7800.0,  # 2.16 hours in seconds
                }
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [-87.63, 41.88],
                    [-88.20, 41.95],
                    [-89.50, 41.70],
                ],
            },
        },
    ],
}

MOCK_ORS_GEOCODE = {
    "features": [
        {
            "properties": {"label": "Chicago, IL, United States"},
            "geometry": {"coordinates": [-87.6298, 41.8781]},
        }
    ]
}


class TestOpenRouteServiceProvider:
    @respx.mock
    def test_get_routes_parses_ors_alternatives(self):
        respx.post("https://api.openrouteservice.org/v2/directions/driving-hgv/geojson").mock(
            return_value=Response(200, json=MOCK_ORS_DIRECTIONS)
        )

        provider = OpenRouteServiceProvider(
            api_key="test-api-key", base_url="https://api.openrouteservice.org"
        )
        origin = Coordinates(lat=41.88, lng=-87.63)
        destination = Coordinates(lat=41.70, lng=-89.50)

        routes = provider.get_routes(origin, destination)

        assert len(routes) == 2
        assert routes[0].id == "route-1"
        assert routes[0].distance_miles == pytest.approx(100.0, abs=0.5)
        assert routes[0].duration_minutes == pytest.approx(120.0, abs=0.5)
        assert len(routes[0].coordinates) == 3
        assert routes[0].geometry  # Non-empty encoded polyline

    @respx.mock
    def test_get_routes_uses_cache_on_subsequent_calls(self):
        route_mock = respx.post(
            "https://api.openrouteservice.org/v2/directions/driving-hgv/geojson"
        ).mock(return_value=Response(200, json=MOCK_ORS_DIRECTIONS))

        provider = OpenRouteServiceProvider(api_key="test-key")
        origin = Coordinates(lat=41.88, lng=-87.63)
        destination = Coordinates(lat=41.70, lng=-89.50)

        routes_1 = provider.get_routes(origin, destination)
        routes_2 = provider.get_routes(origin, destination)

        assert len(routes_1) == len(routes_2)
        assert route_mock.call_count == 1  # Only 1 HTTP call due to cache

    @respx.mock
    def test_get_routes_falls_back_when_ors_fails(self):
        respx.post("https://api.openrouteservice.org/v2/directions/driving-hgv/geojson").mock(
            return_value=Response(500, json={"error": "Server error"})
        )

        provider = OpenRouteServiceProvider(api_key="test-key")
        origin = Coordinates(lat=41.88, lng=-87.63)
        destination = Coordinates(lat=39.74, lng=-104.99)

        # Should fall back to simulated truck routes rather than crashing
        routes = provider.get_routes(origin, destination)
        assert len(routes) == 3
        assert routes[0].distance_miles > 0

    @respx.mock
    def test_geocode_with_ors(self):
        respx.get("https://api.openrouteservice.org/geocode/search").mock(
            return_value=Response(200, json=MOCK_ORS_GEOCODE)
        )

        provider = OpenRouteServiceProvider(api_key="test-key")
        results = provider.geocode("Chicago")

        assert len(results) == 1
        assert results[0].label == "Chicago, IL, United States"
        assert results[0].lat == pytest.approx(41.8781)
        assert results[0].lng == pytest.approx(-87.6298)


class TestRoutingService:
    @respx.mock
    def test_routing_service_generates_routes_and_checkpoints(self):
        respx.post("https://api.openrouteservice.org/v2/directions/driving-hgv/geojson").mock(
            return_value=Response(200, json=MOCK_ORS_DIRECTIONS)
        )

        service = RoutingService(routing_provider=OpenRouteServiceProvider(api_key="test-key"))
        dep_time = datetime(2026, 10, 14, 8, 0, tzinfo=UTC)
        results = service.get_route_options(
            origin=Coordinates(lat=41.88, lng=-87.63),
            destination=Coordinates(lat=41.70, lng=-89.50),
            departure_time=dep_time,
            interval_miles=25.0,
        )

        assert len(results) == 2
        route, checkpoints = results[0]
        assert route.id == "route-1"
        assert len(checkpoints) >= 4
        assert checkpoints[0].mile == 0.0
        assert checkpoints[-1].mile == pytest.approx(route.distance_miles, abs=0.5)
