"""Risk classification engine for individual weather conditions and load overrides.

Classifies wind, rain, and snow based on standard thresholds, then evaluates
truck-specific load weight override rules.
"""

from __future__ import annotations

from apps.risk.domain import CheckpointWeather, RiskLevel


def classify_wind(wind_mph: float) -> tuple[RiskLevel, str]:
    """Classify sustained wind speed into RiskLevel.

    Thresholds:
      < 25 mph       -> Low
      25 to < 35 mph -> Moderate
      35 to < 45 mph -> High
      45 to < 55 mph -> Severe
      >= 55 mph      -> No Travel
    """
    if wind_mph >= 55.0:
        return RiskLevel.NO_TRAVEL, f"Wind {wind_mph:.1f} mph: No Travel"
    if wind_mph >= 45.0:
        return RiskLevel.SEVERE, f"Wind {wind_mph:.1f} mph: Severe"
    if wind_mph >= 35.0:
        return RiskLevel.HIGH, f"Wind {wind_mph:.1f} mph: High"
    if wind_mph >= 25.0:
        return RiskLevel.MODERATE, f"Wind {wind_mph:.1f} mph: Moderate"
    return RiskLevel.LOW, f"Wind {wind_mph:.1f} mph: Low"


def classify_rain(rain_in_per_hr: float) -> tuple[RiskLevel, str]:
    """Classify rain precipitation rate into RiskLevel.

    Thresholds:
      < 0.10 in/hr       -> Low
      0.10 to < 0.25 in/hr -> Moderate
      0.25 to < 0.50 in/hr -> High
      0.50 to 1.00 in/hr  -> Severe (inclusive of 1.00)
      > 1.00 in/hr        -> No Travel
    """
    if rain_in_per_hr > 1.00:
        return RiskLevel.NO_TRAVEL, f"Rain {rain_in_per_hr:.2f} in/hr: No Travel"
    if rain_in_per_hr >= 0.50:
        return RiskLevel.SEVERE, f"Rain {rain_in_per_hr:.2f} in/hr: Severe"
    if rain_in_per_hr >= 0.25:
        return RiskLevel.HIGH, f"Rain {rain_in_per_hr:.2f} in/hr: High"
    if rain_in_per_hr >= 0.10:
        return RiskLevel.MODERATE, f"Rain {rain_in_per_hr:.2f} in/hr: Moderate"
    return RiskLevel.LOW, f"Rain {rain_in_per_hr:.2f} in/hr: Low"


def classify_snow(snow_in_per_hr: float) -> tuple[RiskLevel, str]:
    """Classify snowfall rate into RiskLevel.

    Thresholds:
      < 0.5 in/hr       -> Low
      0.5 to < 1.0 in/hr -> Moderate
      1.0 to < 2.0 in/hr -> High
      2.0 to 3.0 in/hr  -> Severe (inclusive of 3.0)
      > 3.0 in/hr       -> No Travel
    """
    if snow_in_per_hr > 3.0:
        return RiskLevel.NO_TRAVEL, f"Snow {snow_in_per_hr:.2f} in/hr: No Travel"
    if snow_in_per_hr >= 2.0:
        return RiskLevel.SEVERE, f"Snow {snow_in_per_hr:.2f} in/hr: Severe"
    if snow_in_per_hr >= 1.0:
        return RiskLevel.HIGH, f"Snow {snow_in_per_hr:.2f} in/hr: High"
    if snow_in_per_hr >= 0.5:
        return RiskLevel.MODERATE, f"Snow {snow_in_per_hr:.2f} in/hr: Moderate"
    return RiskLevel.LOW, f"Snow {snow_in_per_hr:.2f} in/hr: Low"


def apply_load_rules(
    wind_mph: float,
    load_weight_lb: float,
) -> tuple[RiskLevel | None, str | None]:
    """Evaluate truck load-weight override rules against wind speed.

    Rules:
      1. Wind >= 55 mph, any load                       -> No Travel
      2. Wind 45 to < 55 mph and load > 30,000 lb      -> No Travel
      3. Wind 35 to < 45 mph and load > 40,000 lb      -> Severe

    Load rules can only raise risk or confirm it; they never lower it.
    Returns (elevated_risk_level, reason) or (None, None) if no rule applies.
    """
    if wind_mph >= 55.0:
        return RiskLevel.NO_TRAVEL, f"Wind {wind_mph:.1f} mph (any load): No Travel"

    if 45.0 <= wind_mph < 55.0 and load_weight_lb > 30_000:
        return (
            RiskLevel.NO_TRAVEL,
            f"Wind {wind_mph:.1f} mph with {load_weight_lb:,.0f} lb load (> 30k lb): No Travel",
        )

    if 35.0 <= wind_mph < 45.0 and load_weight_lb > 40_000:
        return (
            RiskLevel.SEVERE,
            f"Wind {wind_mph:.1f} mph with {load_weight_lb:,.0f} lb load (> 40k lb): Severe",
        )

    return None, None


def classify_checkpoint(
    weather: CheckpointWeather,
    load_weight_lb: float,
) -> tuple[RiskLevel, str, dict[str, int]]:
    """Determine final RiskLevel, explanatory reason, and condition levels breakdown.

    Steps:
      1. Evaluate wind, rain, snow against base thresholds.
      2. Compute worst threshold level = max(wind, rain, snow).
      3. Evaluate load rules (which can elevate risk).
      4. Final risk = max(worst_threshold, load_rule_level).
      5. Construct human-readable reason detailing the primary drivers.

    Returns:
      (final_risk, reason, condition_levels)
    """
    wind_risk, _ = classify_wind(weather.wind_mph)
    rain_risk, _ = classify_rain(weather.rain_in_per_hr)
    snow_risk, _ = classify_snow(weather.snow_in_per_hr)

    condition_levels = {
        "wind": int(wind_risk),
        "rain": int(rain_risk),
        "snow": int(snow_risk),
    }

    base_risk = max(wind_risk, rain_risk, snow_risk)
    load_risk, load_reason = apply_load_rules(weather.wind_mph, load_weight_lb)

    # Load rules can only raise risk
    if load_risk is not None and load_risk > base_risk:
        final_risk = load_risk
        reason = load_reason or f"Load rule elevation: {final_risk.label}"
        return final_risk, reason, condition_levels

    final_risk = base_risk

    # Build clear reason identifying which condition(s) drove the risk
    drivers: list[str] = []
    if wind_risk == final_risk and final_risk > RiskLevel.LOW:
        drivers.append(f"Wind {weather.wind_mph:.1f} mph")
    if rain_risk == final_risk and final_risk > RiskLevel.LOW:
        drivers.append(f"Rain {weather.rain_in_per_hr:.2f} in/hr")
    if snow_risk == final_risk and final_risk > RiskLevel.LOW:
        drivers.append(f"Snow {weather.snow_in_per_hr:.2f} in/hr")

    if not drivers:
        # All low
        reason = (
            f"Low risk (Wind {weather.wind_mph:.1f} mph, "
            f"Rain {weather.rain_in_per_hr:.2f} in/hr, "
            f"Snow {weather.snow_in_per_hr:.2f} in/hr)"
        )
    else:
        reason = f"{', '.join(drivers)}: {final_risk.label}"

    return final_risk, reason, condition_levels
