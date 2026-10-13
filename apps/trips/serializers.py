"""Serializers for trips, analysis, heatmap, and geocoding endpoints."""

from __future__ import annotations

from rest_framework import serializers


class CoordinatesSerializer(serializers.Serializer):
    """Geographic point coordinate."""

    lat = serializers.FloatField(
        min_value=-90.0,
        max_value=90.0,
        help_text="Latitude in decimal degrees (-90 to 90)",
    )
    lng = serializers.FloatField(
        min_value=-180.0,
        max_value=180.0,
        help_text="Longitude in decimal degrees (-180 to 180)",
    )
    label = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=255,
        help_text="Human-readable location label (e.g., 'Chicago, IL')",
    )


class TripAnalysisRequestSerializer(serializers.Serializer):
    """Trip parameters for generating weather-aware route analysis."""

    origin = CoordinatesSerializer(help_text="Trip origin coordinate")
    destination = CoordinatesSerializer(help_text="Trip destination coordinate")
    departure_time = serializers.DateTimeField(
        help_text="Departure timestamp in ISO 8601 format"
    )
    load_weight_lb = serializers.FloatField(
        min_value=0.0,
        max_value=150000.0,
        default=40000.0,
        help_text="Truck cargo weight in pounds (used for wind rollover risk overrides)",
    )
    checkpoint_interval_miles = serializers.ChoiceField(
        choices=[10, 25, 50],
        default=25,
        help_text="Distance interval in miles for checkpoint sampling (10, 25, or 50)",
    )


class WeatherDataSerializer(serializers.Serializer):
    """Weather metrics at a specific checkpoint and ETA."""

    wind_mph = serializers.FloatField(help_text="Sustained wind speed in mph")
    rain_in_per_hr = serializers.FloatField(help_text="Rain rate in inches per hour")
    snow_in_per_hr = serializers.FloatField(help_text="Snowfall rate in inches per hour")
    wind_gust_mph = serializers.FloatField(
        required=False, allow_null=True, help_text="Peak wind gust speed in mph"
    )
    temperature_f = serializers.FloatField(
        required=False, allow_null=True, help_text="Ambient temperature in Fahrenheit"
    )


class ConditionLevelsSerializer(serializers.Serializer):
    """Breakdown of individual condition risk scores (0 to 4)."""

    wind = serializers.IntegerField(help_text="Wind risk level: 0 (Low) to 4 (No Travel)")
    rain = serializers.IntegerField(help_text="Rain risk level: 0 (Low) to 4 (No Travel)")
    snow = serializers.IntegerField(help_text="Snow risk level: 0 (Low) to 4 (No Travel)")


class CheckpointSerializer(serializers.Serializer):
    """Weather and risk details for a sampled route checkpoint."""

    mile = serializers.FloatField(help_text="Cumulative odometer mileage along route")
    lat = serializers.FloatField(help_text="Checkpoint latitude")
    lng = serializers.FloatField(help_text="Checkpoint longitude")
    eta = serializers.CharField(help_text="Estimated arrival timestamp in ISO 8601 format")
    weather = WeatherDataSerializer(help_text="Forecasted weather conditions at ETA")
    condition_levels = ConditionLevelsSerializer(help_text="Individual condition risk scores")
    risk = serializers.IntegerField(help_text="Final composite risk level (0 to 4)")
    reason = serializers.CharField(help_text="Plain-English explanation of risk classification")
    segment_miles = serializers.FloatField(help_text="Road segment mileage this checkpoint covers")


class RouteSummarySerializer(serializers.Serializer):
    """Aggregate risk profile and travel metrics for a route."""

    severe_miles = serializers.FloatField(help_text="Miles exposed to Severe conditions")
    high_miles = serializers.FloatField(help_text="Miles exposed to High risk conditions")
    no_travel_miles = serializers.FloatField(help_text="Miles blocked by No Travel conditions")
    average_risk = serializers.FloatField(
        help_text="Distance-weighted average risk score (0 to 4)"
    )
    total_distance_miles = serializers.FloatField(help_text="Total route distance in miles")
    total_duration_minutes = serializers.FloatField(
        help_text="Total estimated driving time in minutes"
    )
    worst_checkpoint = CheckpointSerializer(
        required=False, allow_null=True, help_text="Checkpoint with highest risk rating"
    )


class RouteAnalysisSerializer(serializers.Serializer):
    """Complete analysis and checkpoint profile for a single route option."""

    id = serializers.CharField(help_text="Unique route identifier (e.g., 'route-1')")
    name = serializers.CharField(help_text="Display name for route")
    distance_miles = serializers.FloatField(help_text="Total route distance in miles")
    duration_minutes = serializers.FloatField(help_text="Total driving time in minutes")
    geometry = serializers.CharField(help_text="Google encoded polyline string representing path")
    summary = RouteSummarySerializer(help_text="Aggregated risk summary metrics")
    checkpoints = CheckpointSerializer(many=True, help_text="Sequence of sampled checkpoints")


class TripAnalysisResponseSerializer(serializers.Serializer):
    """Response containing 3 route options, checkpoint risks, and recommendation."""

    routes = RouteAnalysisSerializer(many=True, help_text="Alternative route analyses")
    recommended_route_id = serializers.CharField(help_text="ID of safest recommended route")
    recommendation_reason = serializers.CharField(
        help_text="Explanation justifying why the recommended route was selected"
    )
    ranked_route_ids = serializers.ListField(
        child=serializers.CharField(),
        help_text="Ordered list of route IDs from safest to highest risk",
    )
    all_routes_blocked = serializers.BooleanField(
        help_text="True if all available routes encounter No Travel closures"
    )


class HeatmapRequestSerializer(serializers.Serializer):
    """Parameters for corridor weather heatmap generation."""

    origin = CoordinatesSerializer(help_text="Trip origin coordinate")
    destination = CoordinatesSerializer(help_text="Trip destination coordinate")
    departure_time = serializers.DateTimeField(help_text="Trip departure time in ISO 8601")
    load_weight_lb = serializers.FloatField(
        min_value=0.0,
        max_value=150000.0,
        default=40000.0,
        help_text="Truck load weight in pounds",
    )


class HeatmapPointSerializer(serializers.Serializer):
    lat = serializers.FloatField(help_text="Point latitude")
    lng = serializers.FloatField(help_text="Point longitude")


class HeatmapWeatherMatricesSerializer(serializers.Serializer):
    wind = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField()),
        help_text="Matrix of wind speeds in mph: wind[hour 0..47][point_index]",
    )
    rain = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField()),
        help_text="Matrix of rain rates in in/hr: rain[hour 0..47][point_index]",
    )
    snow = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField()),
        help_text="Matrix of snow rates in in/hr: snow[hour 0..47][point_index]",
    )


class HeatmapResponseSerializer(serializers.Serializer):
    """Corridor weather risk matrix across 48 forecast hours."""

    points = HeatmapPointSerializer(many=True, help_text="Sampled corridor points")
    start_hour = serializers.CharField(help_text="ISO 8601 timestamp for hour index 0")
    risk = serializers.ListField(
        child=serializers.ListField(child=serializers.IntegerField()),
        help_text="Composite risk matrix: risk[hour 0..47][point_index] (0 to 4)",
    )
    weather = HeatmapWeatherMatricesSerializer(help_text="Raw weather value matrices for tooltips")


class GeocodingItemSerializer(serializers.Serializer):
    label = serializers.CharField(help_text="Full address or place name")
    lat = serializers.FloatField(help_text="Latitude")
    lng = serializers.FloatField(help_text="Longitude")


class GeocodingResponseSerializer(serializers.Serializer):
    results = GeocodingItemSerializer(many=True, help_text="Matching location suggestions")
