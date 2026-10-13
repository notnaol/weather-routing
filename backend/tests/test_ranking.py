"""Unit tests for lexicographic route ranking and recommendations."""

import pytest

from apps.risk.domain import RouteAnalysis, RouteSummary
from apps.risk.ranking import rank_routes


def _create_mock_route(
    route_id: str,
    name: str,
    severe_miles: float,
    high_miles: float,
    no_travel_miles: float = 0.0,
    average_risk: float = 1.0,
    duration_minutes: float = 300.0,
    distance_miles: float = 250.0,
) -> RouteAnalysis:
    summary = RouteSummary(
        severe_miles=severe_miles,
        high_miles=high_miles,
        no_travel_miles=no_travel_miles,
        average_risk=average_risk,
        total_distance_miles=distance_miles,
        total_duration_minutes=duration_minutes,
    )
    return RouteAnalysis(
        id=route_id,
        name=name,
        distance_miles=distance_miles,
        duration_minutes=duration_minutes,
        geometry="mock_geometry",
        summary=summary,
        checkpoints=[],
    )


class TestRouteRanking:
    def test_tier_1_fewest_severe_miles_wins(self):
        """Rule 1: Route with fewest Severe miles wins."""
        r1 = _create_mock_route("r1", "Route 1", severe_miles=15.0, high_miles=0.0)
        r2 = _create_mock_route("r2", "Route 2", severe_miles=0.0, high_miles=20.0)
        r3 = _create_mock_route("r3", "Route 3", severe_miles=30.0, high_miles=5.0)

        recommendation = rank_routes([r1, r2, r3])
        assert recommendation.recommended_route_id == "r2"
        assert "fewest Severe miles" in recommendation.recommendation_reason
        assert recommendation.ranked_route_ids == ["r2", "r1", "r3"]

    def test_tier_2_tied_severe_fewest_high_miles_wins(self):
        """Rule 2: When Severe miles tie, fewest High miles wins."""
        # Both have 5.0 Severe miles, but r1 has fewer High miles
        r1 = _create_mock_route("r1", "Route 1", severe_miles=5.0, high_miles=10.0)
        r2 = _create_mock_route("r2", "Route 2", severe_miles=5.0, high_miles=25.0)

        recommendation = rank_routes([r1, r2])
        assert recommendation.recommended_route_id == "r1"
        assert "fewest High risk miles" in recommendation.recommendation_reason

    def test_tier_3_tied_severe_and_high_lowest_avg_risk_wins(self):
        """Rule 3: When Severe and High tie, lowest average risk wins."""
        r1 = _create_mock_route(
            "r1", "Route 1", severe_miles=0.0, high_miles=5.0, average_risk=1.15
        )
        r2 = _create_mock_route(
            "r2", "Route 2", severe_miles=0.0, high_miles=5.0, average_risk=1.65
        )

        recommendation = rank_routes([r1, r2])
        assert recommendation.recommended_route_id == "r1"
        assert "lowest average weather risk" in recommendation.recommendation_reason

    def test_tier_4_tied_risk_shortest_duration_wins(self):
        """Rule 4: When all risk metrics tie, shortest travel time wins."""
        r1 = _create_mock_route(
            "r1",
            "Route 1",
            severe_miles=0.0,
            high_miles=0.0,
            average_risk=0.5,
            duration_minutes=320.0,
        )
        r2 = _create_mock_route(
            "r2",
            "Route 2",
            severe_miles=0.0,
            high_miles=0.0,
            average_risk=0.5,
            duration_minutes=275.0,
        )

        recommendation = rank_routes([r1, r2])
        assert recommendation.recommended_route_id == "r2"
        assert "shortest travel time" in recommendation.recommendation_reason

    def test_unblocked_route_beats_blocked_route(self):
        """Unblocked routes must rank before any route with No Travel conditions."""
        # r1 has No Travel miles, but 0 severe miles and faster time
        r1 = _create_mock_route(
            "r1",
            "Route 1",
            severe_miles=0.0,
            high_miles=0.0,
            no_travel_miles=8.0,
            duration_minutes=180,
        )
        # r2 has 12 Severe miles but NO No Travel miles (clear to travel)
        r2 = _create_mock_route(
            "r2",
            "Route 2",
            severe_miles=12.0,
            high_miles=5.0,
            no_travel_miles=0.0,
            duration_minutes=240,
        )

        recommendation = rank_routes([r1, r2])
        assert recommendation.recommended_route_id == "r2"
        assert recommendation.all_routes_blocked is False
        assert recommendation.ranked_route_ids == ["r2", "r1"]

    def test_all_routes_blocked_least_no_travel_miles_selected_with_warning(self):
        """When all routes are blocked, select the one with fewest No Travel miles and warn."""
        r1 = _create_mock_route(
            "r1", "Route 1", severe_miles=20.0, high_miles=10.0, no_travel_miles=15.0
        )
        r2 = _create_mock_route(
            "r2", "Route 2", severe_miles=10.0, high_miles=10.0, no_travel_miles=4.5
        )
        r3 = _create_mock_route(
            "r3", "Route 3", severe_miles=5.0, high_miles=5.0, no_travel_miles=22.0
        )

        recommendation = rank_routes([r1, r2, r3])
        assert recommendation.recommended_route_id == "r2"
        assert recommendation.all_routes_blocked is True
        assert (
            "Caution: All route options encounter No Travel conditions"
            in recommendation.recommendation_reason
        )
        assert recommendation.ranked_route_ids == ["r2", "r1", "r3"]

    def test_empty_route_list_raises_error(self):
        with pytest.raises(ValueError, match="Cannot rank an empty list"):
            rank_routes([])
