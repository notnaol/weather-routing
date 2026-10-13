"""Unit tests for checkpoint segment miles and route aggregation."""

import pytest

from apps.risk.aggregation import aggregate_route_summary, calculate_segment_miles
from apps.risk.domain import Checkpoint, CheckpointWeather, RiskLevel


class TestSegmentMileageCalculation:
    def test_single_checkpoint_covers_entire_route(self):
        miles = calculate_segment_miles([0.0], 50.0)
        assert miles == [50.0]

    def test_two_checkpoints_split_at_midpoint(self):
        # 0 mi and 50 mi -> midpoint is 25 mi
        miles = calculate_segment_miles([0.0, 50.0], 50.0)
        assert miles == [25.0, 25.0]
        assert sum(miles) == pytest.approx(50.0)

    def test_regular_interval_segments(self):
        # 0, 25, 50, 75, 100 on 100 mi route
        cps = [0.0, 25.0, 50.0, 75.0, 100.0]
        miles = calculate_segment_miles(cps, 100.0)
        assert len(miles) == 5
        # cp 0: [0, 12.5] -> 12.5
        # cp 1: [12.5, 37.5] -> 25.0
        # cp 2: [37.5, 62.5] -> 25.0
        # cp 3: [62.5, 87.5] -> 25.0
        # cp 4: [87.5, 100] -> 12.5
        assert miles == [12.5, 25.0, 25.0, 25.0, 12.5]
        assert sum(miles) == pytest.approx(100.0)

    def test_irregular_destination_boundary(self):
        # 0, 25, 50, 68 (last checkpoint is at destination 68 mi)
        cps = [0.0, 25.0, 50.0, 68.0]
        miles = calculate_segment_miles(cps, 68.0)
        assert len(miles) == 4
        # cp 0: [0, 12.5] -> 12.5
        # cp 1: [12.5, 37.5] -> 25.0
        # cp 2: [37.5, 59.0] -> 21.5
        # cp 3: [59.0, 68.0] -> 9.0
        assert miles == [12.5, 25.0, 21.5, 9.0]
        assert sum(miles) == pytest.approx(68.0)

    def test_zero_distance(self):
        miles = calculate_segment_miles([0.0], 0.0)
        assert miles == [0.0]


class TestRouteSummaryAggregation:
    def _make_checkpoint(
        self,
        mile: float,
        risk: RiskLevel,
        segment_miles: float,
        wind: float = 10.0,
        rain: float = 0.0,
    ) -> Checkpoint:
        return Checkpoint(
            mile=mile,
            lat=40.0,
            lng=-80.0,
            eta="2026-10-14T08:00:00Z",
            weather=CheckpointWeather(wind_mph=wind, rain_in_per_hr=rain, snow_in_per_hr=0.0),
            condition_levels={"wind": int(risk), "rain": 0, "snow": 0},
            risk=risk,
            reason=f"Risk {risk.label}",
            segment_miles=segment_miles,
        )

    def test_aggregation_severe_and_high_miles(self):
        checkpoints = [
            self._make_checkpoint(0.0, RiskLevel.LOW, 12.5),
            self._make_checkpoint(25.0, RiskLevel.HIGH, 25.0),
            self._make_checkpoint(50.0, RiskLevel.SEVERE, 25.0),
            self._make_checkpoint(75.0, RiskLevel.MODERATE, 25.0),
            self._make_checkpoint(100.0, RiskLevel.LOW, 12.5),
        ]
        summary = aggregate_route_summary(
            checkpoints, total_distance_miles=100.0, total_duration_minutes=120.0
        )

        assert summary.severe_miles == 25.0
        assert summary.high_miles == 25.0
        assert summary.no_travel_miles == 0.0
        assert not summary.is_blocked
        # Weighted avg:
        # (0*12.5 + 2*25.0 + 3*25.0 + 1*25.0 + 0*12.5) / 100 = (50 + 75 + 25) / 100 = 1.50
        assert summary.average_risk == 1.50
        assert summary.worst_checkpoint is not None
        assert summary.worst_checkpoint.risk == RiskLevel.SEVERE

    def test_aggregation_with_no_travel_miles(self):
        checkpoints = [
            self._make_checkpoint(0.0, RiskLevel.LOW, 10.0),
            self._make_checkpoint(20.0, RiskLevel.NO_TRAVEL, 20.0),
            self._make_checkpoint(40.0, RiskLevel.SEVERE, 10.0),
        ]
        summary = aggregate_route_summary(
            checkpoints, total_distance_miles=40.0, total_duration_minutes=50.0
        )

        assert summary.no_travel_miles == 20.0
        assert summary.severe_miles == 10.0
        assert summary.is_blocked is True
        assert summary.worst_checkpoint is not None
        assert summary.worst_checkpoint.risk == RiskLevel.NO_TRAVEL

    def test_empty_checkpoints(self):
        summary = aggregate_route_summary([], total_distance_miles=0.0, total_duration_minutes=0.0)
        assert summary.severe_miles == 0.0
        assert summary.high_miles == 0.0
        assert summary.no_travel_miles == 0.0
        assert summary.average_risk == 0.0
        assert summary.worst_checkpoint is None
