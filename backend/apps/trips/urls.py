"""Trips API URL configuration."""

from django.urls import path

from . import views

urlpatterns = [
    path("health", views.health_check, name="health-check"),
    path("geocode", views.geocode, name="geocode"),
    path("trips/analyze", views.analyze_trip, name="trip-analyze"),
    path("trips/heatmap", views.corridor_heatmap, name="trip-heatmap"),
]
