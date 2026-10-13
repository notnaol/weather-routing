"""Unit tests for geometry, polyline algorithms, and trajectory checkpoint sampling."""

from datetime import UTC, datetime

import pytest

from apps.routing.geometry import (
    build_route_points,
    decode_polyline,
    encode_polyline,
    haversine_distance_miles,
    sample_checkpoints_along_route,
)


class TestHaversineDistance:
    def test_zero_distance_same_point(self):
        dist = haversine_distance_miles(41.88, -87.63, 41.88, -87.63)
        assert dist == pytest.approx(0.0)

    def test_known_city_distance(self):
        # Chicago (41.88, -87.63) to Denver (39.74, -104.99)
        # Expected great circle distance is ~920 miles
        dist = haversine_distance_miles(41.88, -87.63, 39.74, -104.99)
        assert 900.0 < dist < 940.0


class TestPolylineEncoding:
    def test_roundtrip_polyline_preserves_coordinates(self):
        coords = [
            (38.5, -120.2),
            (40.7, -120.95),
            (43.252, -126.453),
        ]
        encoded = encode_polyline(coords)
        decoded = decode_polyline(encoded)

        assert len(decoded) == len(coords)
        for (lat1, lng1), (lat2, lng2) in zip(coords, decoded, strict=True):
            assert lat1 == pytest.approx(lat2, abs=1e-5)
            assert lng1 == pytest.approx(lng2, abs=1e-5)


class TestRoutePointsBuilding:
    def test_monotonic_cumulative_distance(self):
        coords = [
            (41.88, -87.63),
            (41.80, -88.50),
            (41.60, -90.00),
            (39.74, -104.99),
        ]
        points = build_route_points(coords, total_duration_seconds=36000.0)
        assert len(points) == 4
        assert points[0].cumulative_distance_miles == 0.0
        assert points[0].cumulative_duration_seconds == 0.0

        for i in range(len(points) - 1):
            assert points[i + 1].cumulative_distance_miles > points[i].cumulative_distance_miles
            assert (
                points[i + 1].cumulative_duration_seconds > points[i].cumulative_duration_seconds
            )

        assert points[-1].cumulative_duration_seconds == pytest.approx(36000.0)


class TestCheckpointSampling:
    def _create_straight_route_points(self, total_miles: float, total_duration_sec: float):
        num_points = 50
        coords = []
        for i in range(num_points + 1):
            t = i / float(num_points)
            # Straight north
            lat = 40.0 + t * (total_miles / 69.0)  # ~69 miles per degree lat
            coords.append((lat, -80.0))
        return build_route_points(coords, total_duration_sec)

    @pytest.mark.parametrize("interval", [10.0, 25.0, 50.0])
    def test_checkpoint_spacing_and_destination_always_included(self, interval: float):
        route_points = self._create_straight_route_points(
            total_miles=115.0, total_duration_sec=7200.0
        )
        dep_time = datetime(2026, 10, 14, 8, 0, tzinfo=UTC)

        cps = sample_checkpoints_along_route(
            route_points, interval_miles=interval, departure_time=dep_time
        )

        # Mile 0 must be included
        assert cps[0].mile == 0.0
        assert cps[0].eta == dep_time

        # Destination must be the final checkpoint
        final_dist = route_points[-1].cumulative_distance_miles
        assert cps[-1].mile == pytest.approx(final_dist, abs=0.2)

        # Verify checkpoints are strictly monotonically increasing in mile and ETA
        for i in range(len(cps) - 1):
            assert cps[i + 1].mile > cps[i].mile
            assert cps[i + 1].eta > cps[i].eta

    def test_eta_calculation_across_multi_hour_route(self):
        # 300-mile route taking 5 hours (18,000 seconds)
        route_points = self._create_straight_route_points(
            total_miles=300.0, total_duration_sec=18000.0
        )
        dep_time = datetime(2026, 10, 14, 6, 0, tzinfo=UTC)

        cps = sample_checkpoints_along_route(
            route_points, interval_miles=50.0, departure_time=dep_time
        )

        # Midpoint (~150 miles) should have ETA roughly 2.5 hours after departure
        mid_cp = next(c for c in cps if abs(c.mile - 150.0) < 5.0)
        elapsed_hours = (mid_cp.eta - dep_time).total_seconds() / 3600.0
        assert 2.3 < elapsed_hours < 2.7

        # Final checkpoint should have ETA ~5 hours after departure
        final_elapsed = (cps[-1].eta - dep_time).total_seconds() / 3600.0
        assert 4.8 < final_elapsed < 5.2
