"""Route aggregation metrics.

Computes segment-weighted exposure miles (Severe, High, No Travel) and
distance-weighted average risk scores.
"""

from __future__ import annotations

from apps.risk.domain import Checkpoint, RiskLevel, RouteSummary


def calculate_segment_miles(
    checkpoint_miles: list[float],
    total_distance_miles: float,
) -> list[float]:
    """Calculate the road stretch each checkpoint represents.

    Each checkpoint covers from the midpoint with the previous checkpoint to
    the midpoint with the next checkpoint:
      - Checkpoint 0: [0, (m0 + m1)/2]
      - Checkpoint i: [(m_{i-1} + mi)/2, (mi + m_{i+1})/2]
      - Checkpoint n-1: [(m_{n-2} + m_{n-1})/2, total_distance]

    Guarantees sum(segment_miles) == total_distance_miles (within float precision).
    """
    n = len(checkpoint_miles)
    if n == 0:
        return []
    if n == 1:
        return [max(0.0, total_distance_miles)]

    total = max(total_distance_miles, checkpoint_miles[-1])
    if total <= 0:
        return [0.0] * n

    # Calculate midpoints
    midpoints = [(checkpoint_miles[i] + checkpoint_miles[i + 1]) / 2.0 for i in range(n - 1)]

    segment_lengths: list[float] = []

    # First checkpoint covers [0, midpoint[0]]
    segment_lengths.append(max(0.0, midpoints[0]))

    # Intermediate checkpoints cover [midpoint[i-1], midpoint[i]]
    for i in range(1, n - 1):
        segment_lengths.append(max(0.0, midpoints[i] - midpoints[i - 1]))

    # Last checkpoint covers [midpoint[-1], total]
    segment_lengths.append(max(0.0, total - midpoints[-1]))

    return segment_lengths


def aggregate_route_summary(
    checkpoints: list[Checkpoint],
    total_distance_miles: float,
    total_duration_minutes: float,
) -> RouteSummary:
    """Aggregate checkpoint-level risks into route-level metrics.

    Calculates:
      - severe_miles: miles under Severe conditions
      - high_miles: miles under High conditions
      - no_travel_miles: miles under No Travel conditions
      - average_risk: distance-weighted mean risk score (0 to 4), rounded to 2 decimals
      - worst_checkpoint: highest risk checkpoint along the route
    """
    if not checkpoints:
        return RouteSummary(
            severe_miles=0.0,
            high_miles=0.0,
            no_travel_miles=0.0,
            average_risk=0.0,
            total_distance_miles=total_distance_miles,
            total_duration_minutes=total_duration_minutes,
            worst_checkpoint=None,
        )

    severe_miles = 0.0
    high_miles = 0.0
    no_travel_miles = 0.0
    weighted_risk_sum = 0.0
    worst_cp: Checkpoint | None = checkpoints[0]

    for cp in checkpoints:
        seg_miles = cp.segment_miles

        if cp.risk == RiskLevel.NO_TRAVEL:
            no_travel_miles += seg_miles
        elif cp.risk == RiskLevel.SEVERE:
            severe_miles += seg_miles
        elif cp.risk == RiskLevel.HIGH:
            high_miles += seg_miles

        weighted_risk_sum += int(cp.risk) * seg_miles

        if worst_cp is None or cp.risk > worst_cp.risk:
            worst_cp = cp

    dist = max(total_distance_miles, 0.001)
    average_risk = round(weighted_risk_sum / dist, 2)

    return RouteSummary(
        severe_miles=round(severe_miles, 1),
        high_miles=round(high_miles, 1),
        no_travel_miles=round(no_travel_miles, 1),
        average_risk=average_risk,
        total_distance_miles=round(total_distance_miles, 1),
        total_duration_minutes=round(total_duration_minutes, 1),
        worst_checkpoint=worst_cp,
    )
