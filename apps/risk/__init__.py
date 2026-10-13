"""Risk calculation and analysis package."""

from apps.risk.aggregation import aggregate_route_summary, calculate_segment_miles
from apps.risk.classifier import (
    apply_load_rules,
    classify_checkpoint,
    classify_rain,
    classify_snow,
    classify_wind,
)
from apps.risk.domain import (
    Checkpoint,
    CheckpointWeather,
    RiskLevel,
    RouteAnalysis,
    RouteRecommendation,
    RouteSummary,
)
from apps.risk.ranking import rank_routes

__all__ = [
    "Checkpoint",
    "CheckpointWeather",
    "RiskLevel",
    "RouteAnalysis",
    "RouteRecommendation",
    "RouteSummary",
    "aggregate_route_summary",
    "apply_load_rules",
    "calculate_segment_miles",
    "classify_checkpoint",
    "classify_rain",
    "classify_snow",
    "classify_wind",
    "rank_routes",
]
