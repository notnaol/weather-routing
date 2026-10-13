"""High-level routing service that orchestrates providers and geometry interpolation."""

from __future__ import annotations

from datetime import datetime

from apps.routing.domain import (
    Coordinates,
    GeocodingResult,
    RawRoute,
    SampledCheckpoint,
)
from apps.routing.geometry import sample_checkpoints_along_route
from apps.routing.providers import (
    GeocodingProvider,
    OpenRouteServiceProvider,
    RoutingProvider,
)


class RoutingService:
    """Service for obtaining truck route alternatives and sampling regular checkpoints."""

    def __init__(
        self,
        routing_provider: RoutingProvider | None = None,
        geocoding_provider: GeocodingProvider | None = None,
    ):
        default_provider = OpenRouteServiceProvider()
        self.routing_provider = routing_provider or default_provider
        self.geocoding_provider = geocoding_provider or default_provider

    def geocode(self, query: str) -> list[GeocodingResult]:
        """Search and autocomplete address or place query."""
        return self.geocoding_provider.geocode(query)

    def get_route_options(
        self,
        origin: Coordinates,
        destination: Coordinates,
        departure_time: datetime,
        interval_miles: float = 25.0,
    ) -> list[tuple[RawRoute, list[SampledCheckpoint]]]:
        """Generate route alternatives and sample checkpoints with calculated ETAs.

        Returns:
          List of (RawRoute, list[SampledCheckpoint]) tuples.
        """
        raw_routes = self.routing_provider.get_routes(origin, destination)
        if not raw_routes:
            return []

        results: list[tuple[RawRoute, list[SampledCheckpoint]]] = []
        for route in raw_routes:
            checkpoints = sample_checkpoints_along_route(
                route.route_points,
                interval_miles=interval_miles,
                departure_time=departure_time,
            )
            results.append((route, checkpoints))

        return results
