"""Unit tests for condition thresholds and load rules classifier."""

import pytest

from apps.risk.classifier import (
    apply_load_rules,
    classify_checkpoint,
    classify_rain,
    classify_snow,
    classify_wind,
)
from apps.risk.domain import CheckpointWeather, RiskLevel


class TestWindClassification:
    @pytest.mark.parametrize(
        ("wind_mph", "expected_level"),
        [
            (0.0, RiskLevel.LOW),
            (15.0, RiskLevel.LOW),
            (24.9, RiskLevel.LOW),
            (25.0, RiskLevel.MODERATE),
            (30.0, RiskLevel.MODERATE),
            (34.9, RiskLevel.MODERATE),
            (35.0, RiskLevel.HIGH),
            (40.0, RiskLevel.HIGH),
            (44.9, RiskLevel.HIGH),
            (45.0, RiskLevel.SEVERE),
            (50.0, RiskLevel.SEVERE),
            (54.9, RiskLevel.SEVERE),
            (55.0, RiskLevel.NO_TRAVEL),
            (65.0, RiskLevel.NO_TRAVEL),
        ],
    )
    def test_wind_threshold_boundaries(self, wind_mph: float, expected_level: RiskLevel):
        level, reason = classify_wind(wind_mph)
        assert level == expected_level
        assert expected_level.label in reason


class TestRainClassification:
    @pytest.mark.parametrize(
        ("rain_in_per_hr", "expected_level"),
        [
            (0.0, RiskLevel.LOW),
            (0.05, RiskLevel.LOW),
            (0.09, RiskLevel.LOW),
            (0.10, RiskLevel.MODERATE),
            (0.20, RiskLevel.MODERATE),
            (0.24, RiskLevel.MODERATE),
            (0.25, RiskLevel.HIGH),
            (0.35, RiskLevel.HIGH),
            (0.49, RiskLevel.HIGH),
            (0.50, RiskLevel.SEVERE),
            (0.75, RiskLevel.SEVERE),
            (1.00, RiskLevel.SEVERE),  # 1.00 is inclusive Severe
            (1.01, RiskLevel.NO_TRAVEL),  # > 1.00 is No Travel
            (2.50, RiskLevel.NO_TRAVEL),
        ],
    )
    def test_rain_threshold_boundaries(self, rain_in_per_hr: float, expected_level: RiskLevel):
        level, reason = classify_rain(rain_in_per_hr)
        assert level == expected_level
        assert expected_level.label in reason


class TestSnowClassification:
    @pytest.mark.parametrize(
        ("snow_in_per_hr", "expected_level"),
        [
            (0.0, RiskLevel.LOW),
            (0.2, RiskLevel.LOW),
            (0.49, RiskLevel.LOW),
            (0.50, RiskLevel.MODERATE),
            (0.80, RiskLevel.MODERATE),
            (0.99, RiskLevel.MODERATE),
            (1.00, RiskLevel.HIGH),
            (1.50, RiskLevel.HIGH),
            (1.99, RiskLevel.HIGH),
            (2.00, RiskLevel.SEVERE),
            (2.80, RiskLevel.SEVERE),
            (3.00, RiskLevel.SEVERE),  # 3.0 is inclusive Severe
            (3.01, RiskLevel.NO_TRAVEL),  # > 3.0 is No Travel
            (4.50, RiskLevel.NO_TRAVEL),
        ],
    )
    def test_snow_threshold_boundaries(self, snow_in_per_hr: float, expected_level: RiskLevel):
        level, reason = classify_snow(snow_in_per_hr)
        assert level == expected_level
        assert expected_level.label in reason


class TestLoadRules:
    def test_rule_1_extreme_wind_any_load(self):
        """Wind >= 55 mph, any load -> No Travel."""
        for weight in [5_000, 20_000, 45_000, 80_000]:
            level, reason = apply_load_rules(wind_mph=55.0, load_weight_lb=weight)
            assert level == RiskLevel.NO_TRAVEL
            assert "No Travel" in reason

            level_high, _ = apply_load_rules(wind_mph=62.0, load_weight_lb=weight)
            assert level_high == RiskLevel.NO_TRAVEL

    def test_rule_2_wind_45_to_54_weight_boundary(self):
        """Wind 45-54 mph and load > 30,000 lb -> No Travel."""
        # At boundary: 30,000 lb does NOT trigger override
        level_boundary, _ = apply_load_rules(wind_mph=48.0, load_weight_lb=30_000)
        assert level_boundary is None

        # Just over boundary: 30,001 lb triggers override
        level_over, reason_over = apply_load_rules(wind_mph=48.0, load_weight_lb=30_001)
        assert level_over == RiskLevel.NO_TRAVEL
        assert "No Travel" in reason_over

        # Heavy load
        level_heavy, _ = apply_load_rules(wind_mph=52.0, load_weight_lb=42_000)
        assert level_heavy == RiskLevel.NO_TRAVEL

    def test_rule_3_wind_35_to_44_weight_boundary(self):
        """Wind 35-44 mph and load > 40,000 lb -> Severe."""
        # At boundary: 40,000 lb does NOT trigger override
        level_boundary, _ = apply_load_rules(wind_mph=40.0, load_weight_lb=40_000)
        assert level_boundary is None

        # Just over boundary: 40,001 lb triggers override
        level_over, reason_over = apply_load_rules(wind_mph=40.0, load_weight_lb=40_001)
        assert level_over == RiskLevel.SEVERE
        assert "Severe" in reason_over

        # Light load under high wind stays without override
        level_light, _ = apply_load_rules(wind_mph=40.0, load_weight_lb=25_000)
        assert level_light is None


class TestCheckpointClassification:
    def test_worst_condition_combination(self):
        """Worst condition across wind, rain, and snow dictates base level."""
        # Rain is Severe (0.6 in/hr), Wind is Low (10 mph), Snow is Low (0)
        weather = CheckpointWeather(wind_mph=10.0, rain_in_per_hr=0.6, snow_in_per_hr=0.0)
        level, reason, conds = classify_checkpoint(weather, load_weight_lb=20_000)
        assert level == RiskLevel.SEVERE
        assert conds["rain"] == int(RiskLevel.SEVERE)
        assert conds["wind"] == int(RiskLevel.LOW)
        assert "Rain" in reason

    def test_snow_no_travel_overrides_moderate_wind(self):
        weather = CheckpointWeather(wind_mph=30.0, rain_in_per_hr=0.0, snow_in_per_hr=3.5)
        level, reason, conds = classify_checkpoint(weather, load_weight_lb=25_000)
        assert level == RiskLevel.NO_TRAVEL
        assert conds["snow"] == int(RiskLevel.NO_TRAVEL)
        assert conds["wind"] == int(RiskLevel.MODERATE)
        assert "Snow" in reason

    def test_load_rule_elevates_risk(self):
        """Load rule elevates wind from High (38 mph) to Severe when load > 40k lb."""
        weather = CheckpointWeather(wind_mph=38.0, rain_in_per_hr=0.0, snow_in_per_hr=0.0)
        level, reason, _ = classify_checkpoint(weather, load_weight_lb=42_000)
        assert level == RiskLevel.SEVERE
        assert "42,000 lb" in reason

    def test_load_rule_only_raises_risk(self):
        """Load rules never decrease risk."""
        # Rain is Severe (0.8 in/hr), Wind is 20 mph with heavy load
        weather = CheckpointWeather(wind_mph=20.0, rain_in_per_hr=0.8, snow_in_per_hr=0.0)
        level, reason, _ = classify_checkpoint(weather, load_weight_lb=50_000)
        assert level == RiskLevel.SEVERE
        assert "Rain" in reason

    def test_clear_conditions_return_low(self):
        weather = CheckpointWeather(wind_mph=12.0, rain_in_per_hr=0.0, snow_in_per_hr=0.0)
        level, reason, conds = classify_checkpoint(weather, load_weight_lb=35_000)
        assert level == RiskLevel.LOW
        assert all(c == int(RiskLevel.LOW) for c in conds.values())
        assert "Low risk" in reason
