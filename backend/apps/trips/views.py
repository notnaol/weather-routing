"""API views for health, address geocoding, route analysis, and corridor heatmap."""

from __future__ import annotations

import logging

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from apps.routing.domain import Coordinates
from apps.trips.serializers import (
    GeocodingResponseSerializer,
    HeatmapRequestSerializer,
    HeatmapResponseSerializer,
    TripAnalysisRequestSerializer,
    TripAnalysisResponseSerializer,
)
from apps.trips.service import NoRouteFoundError, TripService

logger = logging.getLogger(__name__)

trip_service = TripService()


@extend_schema(
    summary="Health check",
    description="Returns the status of the service to verify availability.",
    responses={200: OpenApiResponse(description="Service is healthy")},
    tags=["Health"],
)
@api_view(["GET"])
def health_check(request: Request) -> Response:
    """Health check endpoint for container and hosting monitoring."""
    return Response({"status": "ok"}, status=status.HTTP_200_OK)


@extend_schema(
    summary="Address geocoding autocomplete",
    description="Search for origin or destination addresses with cached geocoding.",
    parameters=[
        OpenApiParameter(
            name="q",
            type=str,
            location=OpenApiParameter.QUERY,
            required=True,
            description="Address or place query (e.g., 'Chicago, IL')",
        )
    ],
    responses={
        200: GeocodingResponseSerializer,
        400: OpenApiResponse(description="Missing search query"),
    },
    tags=["Geocoding"],
)
@api_view(["GET"])
def geocode(request: Request) -> Response:
    """Address autocomplete and geocoding endpoint."""
    query = request.query_params.get("q", "").strip()
    if not query:
        return Response(
            {"error": "Query parameter 'q' is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    results = trip_service.geocode(query)
    return Response({"results": results}, status=status.HTTP_200_OK)


@extend_schema(
    summary="Analyze weather-aware truck routes",
    description=(
        "Generates 3 route alternatives, samples weather along checkpoints at truck ETA, "
        "calculates risk and load rules, and returns the safest recommended route."
    ),
    request=TripAnalysisRequestSerializer,
    responses={
        200: TripAnalysisResponseSerializer,
        400: OpenApiResponse(description="Invalid trip parameters"),
        422: OpenApiResponse(description="No feasible routes found between points"),
        502: OpenApiResponse(description="Upstream routing or weather provider error"),
    },
    tags=["Trips"],
)
@api_view(["POST"])
def analyze_trip(request: Request) -> Response:
    """Main route analysis and risk evaluation endpoint."""
    serializer = TripAnalysisRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    validated = serializer.validated_data
    origin = Coordinates(
        lat=validated["origin"]["lat"],
        lng=validated["origin"]["lng"],
        label=validated["origin"].get("label"),
    )
    destination = Coordinates(
        lat=validated["destination"]["lat"],
        lng=validated["destination"]["lng"],
        label=validated["destination"].get("label"),
    )

    try:
        result = trip_service.analyze_trip(
            origin=origin,
            destination=destination,
            departure_time=validated["departure_time"],
            load_weight_lb=validated["load_weight_lb"],
            checkpoint_interval_miles=float(validated["checkpoint_interval_miles"]),
        )
        return Response(result, status=status.HTTP_200_OK)
    except NoRouteFoundError as e:
        return Response({"error": str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    except Exception as e:
        logger.exception("Error executing trip analysis: %s", e)
        return Response(
            {"error": f"Trip analysis failed: {e!s}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )


@extend_schema(
    summary="Corridor weather risk heatmap",
    description=(
        "Returns a 0-48h weather risk matrix along the trip corridor points for time scrubbing."
    ),
    request=HeatmapRequestSerializer,
    responses={
        200: HeatmapResponseSerializer,
        400: OpenApiResponse(description="Invalid request parameters"),
        422: OpenApiResponse(description="No corridor routes found"),
        502: OpenApiResponse(description="Weather provider error"),
    },
    tags=["Heatmap"],
)
@api_view(["POST"])
def corridor_heatmap(request: Request) -> Response:
    """Generates 0-48 hour weather risk matrix along route corridor."""
    serializer = HeatmapRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    validated = serializer.validated_data
    origin = Coordinates(
        lat=validated["origin"]["lat"],
        lng=validated["origin"]["lng"],
        label=validated["origin"].get("label"),
    )
    destination = Coordinates(
        lat=validated["destination"]["lat"],
        lng=validated["destination"]["lng"],
        label=validated["destination"].get("label"),
    )

    try:
        heatmap_data = trip_service.generate_corridor_heatmap(
            origin=origin,
            destination=destination,
            departure_time=validated["departure_time"],
            load_weight_lb=validated["load_weight_lb"],
        )
        return Response(heatmap_data, status=status.HTTP_200_OK)
    except NoRouteFoundError as e:
        return Response({"error": str(e)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
    except Exception as e:
        logger.exception("Error generating corridor heatmap: %s", e)
        return Response(
            {"error": f"Heatmap generation failed: {e!s}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )
