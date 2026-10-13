"""Geometry calculations, polyline encoding/decoding, and trajectory interpolation."""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from apps.routing.domain import RoutePoint, SampledCheckpoint

EARTH_RADIUS_MILES = 3958.8


def haversine_distance_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in miles."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_MILES * c


def encode_polyline(coordinates: list[tuple[float, float]], precision: int = 5) -> str:
    """Encode a list of (lat, lng) tuples into an encoded polyline string."""
    factor = 10**precision
    output: list[str] = []
    prev_lat = 0
    prev_lng = 0

    for lat, lng in coordinates:
        late5 = round(lat * factor)
        lnge5 = round(lng * factor)

        d_lat = late5 - prev_lat
        d_lng = lnge5 - prev_lng

        prev_lat = late5
        prev_lng = lnge5

        for val in (d_lat, d_lng):
            val = ~(val << 1) if val < 0 else (val << 1)
            while val >= 0x20:
                output.append(chr((0x20 | (val & 0x1F)) + 63))
                val >>= 5
            output.append(chr(val + 63))

    return "".join(output)


def decode_polyline(polyline_str: str, precision: int = 5) -> list[tuple[float, float]]:
    """Decode an encoded polyline string into a list of (lat, lng) tuples."""
    factor = 10**precision
    coordinates: list[tuple[float, float]] = []
    index = 0
    lat = 0
    lng = 0
    length = len(polyline_str)

    while index < length:
        # Decode latitude
        shift = 0
        result = 0
        while True:
            byte = ord(polyline_str[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        d_lat = ~(result >> 1) if (result & 1) else (result >> 1)
        lat += d_lat

        # Decode longitude
        shift = 0
        result = 0
        while True:
            byte = ord(polyline_str[index]) - 63
            index += 1
            result |= (byte & 0x1F) << shift
            shift += 5
            if byte < 0x20:
                break
        d_lng = ~(result >> 1) if (result & 1) else (result >> 1)
        lng += d_lng

        coordinates.append((lat / factor, lng / factor))

    return coordinates


def build_route_points(
    coordinates: list[tuple[float, float]],
    total_duration_seconds: float,
    total_distance_miles: float | None = None,
) -> list[RoutePoint]:
    """Convert a sequence of (lat, lng) into RoutePoints with cumulative distance and duration.

    If total_distance_miles is provided, scales cumulative distance along the geometry
    to match the exact odometer distance reported by the routing provider.
    """
    if not coordinates:
        return []

    if len(coordinates) == 1:
        lat, lng = coordinates[0]
        final_dist = total_distance_miles if total_distance_miles is not None else 0.0
        return [
            RoutePoint(
                lat=lat,
                lng=lng,
                cumulative_distance_miles=final_dist,
                cumulative_duration_seconds=total_duration_seconds,
            )
        ]

    # Calculate cumulative distances
    distances: list[float] = [0.0]
    total_dist = 0.0
    for i in range(len(coordinates) - 1):
        lat1, lng1 = coordinates[i]
        lat2, lng2 = coordinates[i + 1]
        dist = haversine_distance_miles(lat1, lng1, lat2, lng2)
        total_dist += dist
        distances.append(total_dist)

    # Scale to match provider's reported road network distance if given
    if total_distance_miles is not None and total_dist > 0:
        scale = total_distance_miles / total_dist
        distances = [d * scale for d in distances]
        total_dist = total_distance_miles

    # Distribute duration proportionally to segment distance
    points: list[RoutePoint] = []
    for i, (lat, lng) in enumerate(coordinates):
        cum_dist = distances[i]
        fraction = (cum_dist / total_dist) if total_dist > 0 else 0.0
        cum_duration = fraction * total_duration_seconds
        points.append(
            RoutePoint(
                lat=lat,
                lng=lng,
                cumulative_distance_miles=cum_dist,
                cumulative_duration_seconds=cum_duration,
            )
        )

    return points


def sample_checkpoints_along_route(
    route_points: list[RoutePoint],
    interval_miles: float,
    departure_time: datetime,
) -> list[SampledCheckpoint]:
    """Sample checkpoints at regular mileage intervals along the route.

    Guarantees:
      - Mile 0 is always included.
      - Checkpoints occur every `interval_miles` (10, 25, or 50).
      - The destination (final point) is ALWAYS included.
      - Linear interpolation of position and cumulative duration between route points.
    """
    if not route_points:
        return []

    total_miles = route_points[-1].cumulative_distance_miles

    # Build list of target mile markers
    target_miles: list[float] = [0.0]
    current = 0.0
    # Avoid having a checkpoint within 1.0 mile of destination before destination
    while current + interval_miles < max(0.0, total_miles - 1.0):
        current += interval_miles
        target_miles.append(current)

    if total_miles > 0 and (not target_miles or target_miles[-1] < total_miles):
        target_miles.append(total_miles)

    checkpoints: list[SampledCheckpoint] = []
    pt_idx = 0
    num_pts = len(route_points)

    for target in target_miles:
        # Advance pt_idx until route_points[pt_idx + 1] exceeds or equals target
        while pt_idx < num_pts - 2 and route_points[pt_idx + 1].cumulative_distance_miles < target:
            pt_idx += 1

        p1 = route_points[pt_idx]
        p2 = route_points[min(pt_idx + 1, num_pts - 1)]

        seg_dist = p2.cumulative_distance_miles - p1.cumulative_distance_miles
        if seg_dist > 0.0001:
            t = max(0.0, min(1.0, (target - p1.cumulative_distance_miles) / seg_dist))
        else:
            t = 0.0

        lat = p1.lat + t * (p2.lat - p1.lat)
        lng = p1.lng + t * (p2.lng - p1.lng)
        duration_sec = p1.cumulative_duration_seconds + t * (
            p2.cumulative_duration_seconds - p1.cumulative_duration_seconds
        )
        eta = departure_time + timedelta(seconds=duration_sec)

        checkpoints.append(
            SampledCheckpoint(
                mile=round(target, 1),
                lat=round(lat, 6),
                lng=round(lng, 6),
                cumulative_duration_seconds=duration_sec,
                eta=eta,
            )
        )

    return checkpoints
