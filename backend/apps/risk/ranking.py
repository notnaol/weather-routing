"""Route ranking and recommendation engine.

Implements strict lexicographic sorting to determine the safest and most efficient route:
  1. Fewest Severe miles
  2. Fewest High miles
  3. Lowest average risk
  4. Shortest travel time

Handles No Travel road closures by isolating blocked routes and warning the driver.
"""

from __future__ import annotations

from apps.risk.domain import RouteAnalysis, RouteRecommendation


def _build_route_sort_key(route: RouteAnalysis) -> tuple[int, float, float, float, float, float]:
    """Generate lexicographic comparison tuple for a route.

    Structure:
      (
        blocked_flag: 0 for clean route, 1 for blocked route,
        no_travel_miles: 0.0 for clean routes, fewer wins among blocked,
        severe_miles: rounded to 0.1,
        high_miles: rounded to 0.1,
        average_risk: rounded to 0.02,
        duration_minutes: rounded to 0.1
      )
    """
    s = route.summary
    is_blocked = 1 if s.is_blocked else 0
    no_travel = round(s.no_travel_miles, 1) if is_blocked else 0.0
    severe = round(s.severe_miles, 1)
    high = round(s.high_miles, 1)
    avg_risk = round(s.average_risk, 2)
    duration = round(route.duration_minutes, 1)

    return (is_blocked, no_travel, severe, high, avg_risk, duration)


def _generate_recommendation_reason(winner: RouteAnalysis, others: list[RouteAnalysis]) -> str:
    """Generate a crisp, human-readable reason explaining why the winner was chosen."""
    if not others:
        if winner.summary.is_blocked:
            return (
                f"Warning: {winner.name} contains No Travel conditions "
                f"({winner.summary.no_travel_miles:.1f} mi)."
            )
        return f"{winner.name} is the only available route option."

    all_blocked = winner.summary.is_blocked and all(o.summary.is_blocked for o in others)
    if all_blocked:
        other_nt = ", ".join(f"{o.name} ({o.summary.no_travel_miles:.1f} mi)" for o in others)
        return (
            f"Caution: All route options encounter No Travel conditions. "
            f"{winner.name} is selected with the fewest blocked miles "
            f"({winner.summary.no_travel_miles:.1f} mi vs {other_nt})."
        )

    # Winner is unblocked, but some others might be blocked
    blocked_others = [o for o in others if o.summary.is_blocked]
    if blocked_others and all(o.summary.is_blocked for o in others):
        return (
            f"{winner.name} is the safest choice: it is the only route completely free "
            f"of No Travel closures."
        )

    # Compare with runner-up (the first other route after sorting)
    runner_up = others[0]
    w_sum = winner.summary
    r_sum = runner_up.summary

    if w_sum.severe_miles < r_sum.severe_miles:
        alt_str = " and ".join(f"{o.summary.severe_miles:.1f} mi" for o in others)
        return (
            f"{winner.name} has the fewest Severe miles "
            f"({w_sum.severe_miles:.1f} mi vs {alt_str} on alternatives)."
        )

    if w_sum.high_miles < r_sum.high_miles:
        alt_str = " and ".join(f"{o.summary.high_miles:.1f} mi" for o in others)
        return (
            f"{winner.name} has the fewest High risk miles "
            f"({w_sum.high_miles:.1f} mi vs {alt_str} on alternatives)."
        )

    if w_sum.average_risk < r_sum.average_risk:
        alt_str = " and ".join(f"{o.summary.average_risk:.2f}" for o in others)
        return (
            f"{winner.name} has the lowest average weather risk "
            f"({w_sum.average_risk:.2f} vs {alt_str} on alternatives)."
        )

    if winner.duration_minutes < runner_up.duration_minutes:
        return (
            f"{winner.name} has the shortest travel time "
            f"({winner.duration_minutes:.0f} min vs {runner_up.duration_minutes:.0f} min) "
            f"with equivalent weather risk."
        )

    return f"{winner.name} provides the optimal balance of weather safety and travel time."


def rank_routes(routes: list[RouteAnalysis]) -> RouteRecommendation:
    """Rank route options according to the brief's lexicographic hierarchy.

    Order:
      1. Fewest Severe miles
      2. Fewest High miles
      3. Lowest average risk
      4. Shortest travel time

    Routes with No Travel conditions are flagged and ranked after unblocked routes.
    """
    if not routes:
        raise ValueError("Cannot rank an empty list of routes")

    # Sort routes using the lexicographic key
    ranked = sorted(routes, key=_build_route_sort_key)
    winner = ranked[0]
    others = ranked[1:]

    all_routes_blocked = all(r.summary.is_blocked for r in routes)
    reason = _generate_recommendation_reason(winner, others)

    return RouteRecommendation(
        recommended_route_id=winner.id,
        recommendation_reason=reason,
        ranked_route_ids=[r.id for r in ranked],
        all_routes_blocked=all_routes_blocked,
        details={
            "winner_name": winner.name,
            "winner_severe_miles": winner.summary.severe_miles,
            "winner_high_miles": winner.summary.high_miles,
            "winner_avg_risk": winner.summary.average_risk,
            "winner_duration_minutes": winner.duration_minutes,
        },
    )
