"""Trip analysis and corridor heatmap orchestration service."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from apps.risk import (
    Checkpoint,
    RouteAnalysis,
    aggregate_route_summary,
    calculate_segment_miles,
    classify_checkpoint,
    rank_routes,
)
from apps.routing import Coordinates, RoutingService, haversine_distance_miles
from apps.weather import WeatherService


class NoRouteFoundError(Exception):
    """Raised when no route options can be determined between origin and destination."""


class TripService:
    """Orchestrates routing, weather enrichment, risk classification, and ranking."""

    def __init__(
        self,
        routing_service: RoutingService | None = None,
        weather_service: WeatherService | None = None,
    ):
        self.routing_service = routing_service or RoutingService()
        self.weather_service = weather_service or WeatherService()

    def analyze_trip(
        self,
        origin: Coordinates,
        destination: Coordinates,
        departure_time: datetime,
        load_weight_lb: float,
        checkpoint_interval_miles: float = 25.0,
    ) -> dict[str, Any]:
        """Perform end-to-end weather-aware route analysis across 3 route options."""
        route_options = self.routing_service.get_route_options(
            origin=origin,
            destination=destination,
            departure_time=departure_time,
            interval_miles=checkpoint_interval_miles,
        )

        if not route_options:
            raise NoRouteFoundError("No feasible routes found between origin and destination.")

        analyzed_routes: list[RouteAnalysis] = []

        for raw_route, sampled_checkpoints in route_options:
            weather_readings = self.weather_service.get_weather_for_checkpoints(
                sampled_checkpoints
            )

            # Calculate road segment miles covered by each checkpoint
            cp_miles = [cp.mile for cp in sampled_checkpoints]
            segment_miles = calculate_segment_miles(cp_miles, raw_route.distance_miles)

            checkpoints: list[Checkpoint] = []
            for scp, w_data, s_len in zip(
                sampled_checkpoints, weather_readings, segment_miles, strict=False
            ):
                risk_level, reason, cond_levels = classify_checkpoint(
                    weather=w_data,
                    load_weight_lb=load_weight_lb,
                )

                checkpoints.append(
                    Checkpoint(
                        mile=scp.mile,
                        lat=scp.lat,
                        lng=scp.lng,
                        eta=scp.eta.isoformat(),
                        weather=w_data,
                        condition_levels=cond_levels,
                        risk=risk_level,
                        reason=reason,
                        segment_miles=s_len,
                    )
                )

            summary = aggregate_route_summary(
                checkpoints=checkpoints,
                total_distance_miles=raw_route.distance_miles,
                total_duration_minutes=raw_route.duration_minutes,
            )

            analyzed_routes.append(
                RouteAnalysis(
                    id=raw_route.id,
                    name=raw_route.name,
                    distance_miles=raw_route.distance_miles,
                    duration_minutes=raw_route.duration_minutes,
                    geometry=raw_route.geometry,
                    summary=summary,
                    checkpoints=checkpoints,
                )
            )

        recommendation = rank_routes(analyzed_routes)

        return {
            "routes": [self._serialize_route(r) for r in analyzed_routes],
            "recommended_route_id": recommendation.recommended_route_id,
            "recommendation_reason": recommendation.recommendation_reason,
            "ranked_route_ids": recommendation.ranked_route_ids,
            "all_routes_blocked": recommendation.all_routes_blocked,
        }

    def generate_corridor_heatmap(
        self,
        origin: Coordinates,
        destination: Coordinates,
        departure_time: datetime,
        load_weight_lb: float,
    ) -> dict[str, Any]:
        """Generate 48-hour weather risk matrix along the trip corridor."""
        route_options = self.routing_service.get_route_options(
            origin=origin,
            destination=destination,
            departure_time=departure_time,
            interval_miles=15.0,
        )

        if not route_options:
            raise NoRouteFoundError("No feasible routes found for heatmap corridor.")

        # Collect points along all routes every ~15 miles
        raw_corridor_points: list[tuple[float, float]] = []
        for _, sampled_checkpoints in route_options:
            for scp in sampled_checkpoints:
                raw_corridor_points.append((scp.lat, scp.lng))

        # De-duplicate points that are within 6 miles of each other
        corridor_points: list[tuple[float, float]] = []
        for pt in raw_corridor_points:
            too_close = any(
                haversine_distance_miles(pt[0], pt[1], kept[0], kept[1]) < 6.0
                for kept in corridor_points
            )
            if not too_close:
                corridor_points.append(pt)

        # Cap corridor points to 60 points max to ensure fast response time
        if len(corridor_points) > 60:
            step = len(corridor_points) / 60.0
            corridor_points = [corridor_points[int(i * step)] for i in range(60)]

        matrix = self.weather_service.get_corridor_heatmap_matrix(
            corridor_points=corridor_points,
            start_time=departure_time,
            load_weight_lb=load_weight_lb,
            hours=48,
        )

        return {
            "points": [{"lat": p[0], "lng": p[1]} for p in matrix.points],
            "start_hour": matrix.start_time_iso,
            "risk": matrix.risk_matrix,
            "weather": {
                "wind": matrix.wind_matrix,
                "rain": matrix.rain_matrix,
                "snow": matrix.snow_matrix,
            },
        }

    def geocode(self, query: str) -> list[dict[str, Any]]:
        """Autocomplete address or location query."""
        results = self.routing_service.geocode(query)
        return [{"label": r.label, "lat": r.lat, "lng": r.lng} for r in results]

    def _serialize_route(self, route: RouteAnalysis) -> dict[str, Any]:
        s = route.summary
        worst_cp = self._serialize_checkpoint(s.worst_checkpoint) if s.worst_checkpoint else None

        return {
            "id": route.id,
            "name": route.name,
            "distance_miles": route.distance_miles,
            "duration_minutes": route.duration_minutes,
            "geometry": route.geometry,
            "summary": {
                "severe_miles": s.severe_miles,
                "high_miles": s.high_miles,
                "no_travel_miles": s.no_travel_miles,
                "average_risk": s.average_risk,
                "total_distance_miles": s.total_distance_miles,
                "total_duration_minutes": s.total_duration_minutes,
                "worst_checkpoint": worst_cp,
            },
            "checkpoints": [self._serialize_checkpoint(cp) for cp in route.checkpoints],
        }

    def _serialize_checkpoint(self, cp: Checkpoint) -> dict[str, Any]:
        return {
            "mile": cp.mile,
            "lat": cp.lat,
            "lng": cp.lng,
            "eta": cp.eta,
            "weather": {
                "wind_mph": cp.weather.wind_mph,
                "rain_in_per_hr": cp.weather.rain_in_per_hr,
                "snow_in_per_hr": cp.weather.snow_in_per_hr,
                "wind_gust_mph": cp.weather.wind_gust_mph,
                "temperature_f": cp.weather.temperature_f,
            },
            "condition_levels": cp.condition_levels,
            "risk": int(cp.risk),
            "reason": cp.reason,
            "segment_miles": round(cp.segment_miles, 1),
        }
