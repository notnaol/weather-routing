"""Integration tests for all REST API endpoints."""

import pytest
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestApiEndpoints:
    def test_health_check_endpoint(self, api_client: APIClient):
        response = api_client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}

    def test_openapi_schema_and_swagger_docs(self, api_client: APIClient):
        # Schema endpoint
        schema_resp = api_client.get("/api/schema/")
        assert schema_resp.status_code == status.HTTP_200_OK

        # Swagger UI HTML
        docs_resp = api_client.get("/api/docs/")
        assert docs_resp.status_code == status.HTTP_200_OK
        assert b"swagger-ui" in docs_resp.content.lower()

    def test_geocode_endpoint_success(self, api_client: APIClient):
        response = api_client.get("/api/v1/geocode?q=Chicago")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)
        if data["results"]:
            assert "lat" in data["results"][0]
            assert "lng" in data["results"][0]
            assert "label" in data["results"][0]

    def test_geocode_endpoint_missing_query(self, api_client: APIClient):
        response = api_client.get("/api/v1/geocode")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.json()

    def test_analyze_trip_endpoint_success(self, api_client: APIClient):
        payload = {
            "origin": {"lat": 41.8781, "lng": -87.6298, "label": "Chicago, IL"},
            "destination": {"lat": 39.7392, "lng": -104.9903, "label": "Denver, CO"},
            "departure_time": "2026-10-14T08:00:00Z",
            "load_weight_lb": 42000.0,
            "checkpoint_interval_miles": 25,
        }
        response = api_client.post("/api/v1/trips/analyze", data=payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "routes" in data
        assert len(data["routes"]) >= 1
        assert "recommended_route_id" in data
        assert "recommendation_reason" in data
        assert "ranked_route_ids" in data

        first_route = data["routes"][0]
        assert "id" in first_route
        assert "name" in first_route
        assert "distance_miles" in first_route
        assert "duration_minutes" in first_route
        assert "geometry" in first_route
        assert "summary" in first_route
        assert "checkpoints" in first_route

        summary = first_route["summary"]
        assert "severe_miles" in summary
        assert "high_miles" in summary
        assert "no_travel_miles" in summary
        assert "average_risk" in summary

        # Checkpoint structure
        checkpoints = first_route["checkpoints"]
        assert len(checkpoints) >= 2
        first_cp = checkpoints[0]
        assert first_cp["mile"] == 0.0
        assert "eta" in first_cp
        assert "weather" in first_cp
        assert "condition_levels" in first_cp
        assert "risk" in first_cp
        assert "reason" in first_cp

    def test_analyze_trip_endpoint_validation_error(self, api_client: APIClient):
        # Invalid payload: missing destination and negative weight
        payload = {
            "origin": {"lat": 41.8781, "lng": -87.6298},
            "departure_time": "2026-10-14T08:00:00Z",
            "load_weight_lb": -500.0,
        }
        response = api_client.post("/api/v1/trips/analyze", data=payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_corridor_heatmap_endpoint_success(self, api_client: APIClient):
        payload = {
            "origin": {"lat": 41.8781, "lng": -87.6298},
            "destination": {"lat": 41.70, "lng": -89.50},
            "departure_time": "2026-10-14T06:00:00Z",
            "load_weight_lb": 35000.0,
        }
        response = api_client.post("/api/v1/trips/heatmap", data=payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "points" in data
        assert "start_hour" in data
        assert "risk" in data
        assert "weather" in data

        assert len(data["risk"]) == 48  # 48 hours
        assert len(data["weather"]["wind"]) == 48
        assert len(data["weather"]["rain"]) == 48
        assert len(data["weather"]["snow"]) == 48

        if data["points"]:
            num_points = len(data["points"])
            assert len(data["risk"][0]) == num_points

    def test_corridor_heatmap_validation_error(self, api_client: APIClient):
        response = api_client.post("/api/v1/trips/heatmap", data={}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
