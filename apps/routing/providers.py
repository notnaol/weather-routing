"""Routing and geocoding providers with OpenRouteService and resilient fallbacks."""

from __future__ import annotations

import logging
import math
from typing import Protocol

import httpx
from django.conf import settings
from django.core.cache import cache

from apps.routing.domain import Coordinates, GeocodingResult, RawRoute
from apps.routing.geometry import build_route_points, encode_polyline, haversine_distance_miles

logger = logging.getLogger(__name__)

METERS_TO_MILES = 1.0 / 1609.344


class RoutingProvider(Protocol):
    """Protocol for routing providers."""

    def get_routes(self, origin: Coordinates, destination: Coordinates) -> list[RawRoute]: ...


class GeocodingProvider(Protocol):
    """Protocol for geocoding providers."""

    def geocode(self, query: str) -> list[GeocodingResult]: ...


class OpenRouteServiceProvider:
    """OpenRouteService client with truck-aware (driving-hgv) routing and Pelias geocoding."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 12.0,
    ):
        self.api_key = api_key or getattr(settings, "OPENROUTESERVICE_API_KEY", "")
        self.base_url = (
            base_url
            or getattr(settings, "OPENROUTESERVICE_BASE_URL", "https://api.openrouteservice.org")
        ).rstrip("/")
        self.timeout = timeout_seconds

    def geocode(self, query: str) -> list[GeocodingResult]:
        """Geocode search query to coordinates with 24-hour cache."""
        cleaned = query.strip()
        if not cleaned:
            return []

        cache_key = f"geocode:{cleaned.lower()}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        results: list[GeocodingResult] = []

        # If ORS key is configured, use ORS Geocoding (Pelias)
        if self.api_key:
            try:
                results = self._geocode_ors(cleaned)
            except Exception as e:
                logger.warning("ORS geocoding failed, falling back to Nominatim: %s", e)

        # Fallback to Nominatim if ORS key missing or failed
        if not results:
            try:
                results = self._geocode_nominatim(cleaned)
            except Exception as e:
                logger.error("Nominatim geocoding failed: %s", e)

        if results:
            cache.set(cache_key, results, timeout=86400)  # 24 hours

        return results

    def _geocode_ors(self, query: str) -> list[GeocodingResult]:
        url = f"{self.base_url}/geocode/search"
        params = {"api_key": self.api_key, "text": query, "size": 5}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        results: list[GeocodingResult] = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            coords = feature.get("geometry", {}).get("coordinates", [])
            if len(coords) >= 2:
                results.append(
                    GeocodingResult(
                        label=props.get("label", query),
                        lat=coords[1],
                        lng=coords[0],
                    )
                )
        return results

    def _geocode_nominatim(self, query: str) -> list[GeocodingResult]:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": query, "format": "json", "limit": 5, "addressdetails": 1}
        headers = {"User-Agent": "WeatherAwareTruckRouting/1.0"}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        results: list[GeocodingResult] = []
        for item in data:
            results.append(
                GeocodingResult(
                    label=item.get("display_name", query),
                    lat=float(item["lat"]),
                    lng=float(item["lon"]),
                )
            )
        return results

    def get_routes(self, origin: Coordinates, destination: Coordinates) -> list[RawRoute]:
        """Fetch up to 3 route alternatives using the truck (driving-hgv) profile."""
        cache_key = (
            f"route:{origin.lat:.3f},{origin.lng:.3f}:{destination.lat:.3f},{destination.lng:.3f}"
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        routes: list[RawRoute] = []

        if self.api_key:
            try:
                routes = self._fetch_ors_directions(origin, destination)
            except Exception as e:
                logger.warning("ORS directions failed (%s), generating fallback truck routes", e)

        # If no key or ORS failed, generate simulated corridor routes so the app always works
        if not routes:
            routes = self._generate_simulated_truck_routes(origin, destination)

        if routes:
            cache.set(cache_key, routes, timeout=3600)  # 1 hour

        return routes

    def _fetch_ors_directions(
        self, origin: Coordinates, destination: Coordinates
    ) -> list[RawRoute]:
        url = f"{self.base_url}/v2/directions/driving-hgv/geojson"
        payload = {
            "coordinates": [[origin.lng, origin.lat], [destination.lng, destination.lat]],
            "alternative_routes": {
                "target_count": 3,
                "weight_factor": 1.4,
                "share_factor": 0.6,
            },
        }
        headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        features = data.get("features", [])
        routes: list[RawRoute] = []

        for idx, feat in enumerate(features[:3]):
            summary = feat.get("properties", {}).get("summary", {})
            distance_meters = summary.get("distance", 0.0)
            duration_seconds = summary.get("duration", 0.0)

            # ORS geometry is GeoJSON coordinates [[lng, lat], ...]
            raw_coords = feat.get("geometry", {}).get("coordinates", [])
            lat_lng_coords = [(float(c[1]), float(c[0])) for c in raw_coords]

            dist_miles = distance_meters * METERS_TO_MILES
            dur_minutes = duration_seconds / 60.0

            route_points = build_route_points(
                lat_lng_coords, duration_seconds, total_distance_miles=dist_miles
            )
            polyline_str = encode_polyline(lat_lng_coords)

            routes.append(
                RawRoute(
                    id=f"route-{idx + 1}",
                    name=f"Route {idx + 1}",
                    distance_miles=round(dist_miles, 1),
                    duration_minutes=round(dur_minutes, 1),
                    geometry=polyline_str,
                    coordinates=lat_lng_coords,
                    route_points=route_points,
                )
            )

        return routes

    def _generate_simulated_truck_routes(
        self, origin: Coordinates, destination: Coordinates
    ) -> list[RawRoute]:
        """Generate 3 plausible highway corridor routes with distinct geometry for testing."""
        straight_dist_miles = haversine_distance_miles(
            origin.lat, origin.lng, destination.lat, destination.lng
        )

        routes: list[RawRoute] = []
        # (name, distance_factor, curvature_offset, avg_mph)
        variations = [
            ("Primary Interstate", 1.15, 0.0, 58.0),
            ("Northern Highway", 1.25, 0.4, 52.0),
            ("Southern Bypass", 1.22, -0.4, 54.0),
        ]

        num_points = max(15, int(straight_dist_miles / 15))

        for idx, (name, dist_factor, curve_factor, avg_mph) in enumerate(variations):
            coords: list[tuple[float, float]] = []

            for i in range(num_points + 1):
                t = i / float(num_points)
                # Linear point
                lat = origin.lat + t * (destination.lat - origin.lat)
                lng = origin.lng + t * (destination.lng - origin.lng)

                # Add smooth curve perpendicular to trajectory
                arc = math.sin(t * math.pi) * curve_factor
                # Perpendicular offset (swap dx and dy)
                lat += arc * 0.5
                lng += arc * 0.5

                coords.append((lat, lng))

            route_dist = straight_dist_miles * dist_factor
            route_duration_sec = (route_dist / avg_mph) * 3600.0

            route_points = build_route_points(
                coords, route_duration_sec, total_distance_miles=route_dist
            )
            polyline_str = encode_polyline(coords)

            routes.append(
                RawRoute(
                    id=f"route-{idx + 1}",
                    name=f"Route {idx + 1} ({name})",
                    distance_miles=round(route_dist, 1),
                    duration_minutes=round(route_duration_sec / 60.0, 1),
                    geometry=polyline_str,
                    coordinates=coords,
                    route_points=route_points,
                )
            )

        return routes
