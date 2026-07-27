"""OpenRouteService geocoding and directions."""
from __future__ import annotations

from typing import Any

import requests
from django.conf import settings
from rest_framework.exceptions import ValidationError


ORS_GEOCODE_URL = "https://api.openrouteservice.org/geocode/search"
ORS_DIRECTIONS_URL = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"


class RoutingError(Exception):
    """Raised when OpenRouteService fails."""


def _api_key() -> str:
    key = settings.OPENROUTESERVICE_API_KEY
    if not key:
        raise ValidationError(
            {"detail": "OPENROUTESERVICE_API_KEY is not configured on the server."}
        )
    return key


def geocode(location: str) -> dict[str, Any]:
    """Resolve a place name to lon/lat coordinates."""
    response = requests.get(
        ORS_GEOCODE_URL,
        params={
            "api_key": _api_key(),
            "text": location,
            "size": 1,
        },
        timeout=30,
    )
    if response.status_code != 200:
        raise RoutingError(f"Geocoding failed for '{location}': {response.text}")

    data = response.json()
    features = data.get("features") or []
    if not features:
        raise ValidationError({"detail": f"Could not find location: '{location}'"})

    feature = features[0]
    lon, lat = feature["geometry"]["coordinates"]
    label = feature.get("properties", {}).get("label", location)
    return {"lon": lon, "lat": lat, "label": label, "name": location}


def get_route(waypoints: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Request a driving route through the given waypoints.

    Each waypoint is a dict with 'lon' and 'lat'.
    Returns GeoJSON geometry plus distance (miles) and duration (hours).
    """
    if len(waypoints) < 2:
        raise ValidationError({"detail": "At least two waypoints are required."})

    coordinates = [[wp["lon"], wp["lat"]] for wp in waypoints]

    response = requests.post(
        ORS_DIRECTIONS_URL,
        json={"coordinates": coordinates},
        headers={
            "Authorization": _api_key(),
            "Content-Type": "application/json",
        },
        timeout=60,
    )
    if response.status_code != 200:
        raise RoutingError(f"Directions request failed: {response.text}")

    data = response.json()
    features = data.get("features") or []
    if not features:
        raise RoutingError("No route found between the given locations.")

    feature = features[0]
    summary = feature["properties"]["summary"]
    # ORS returns meters and seconds
    distance_miles = summary["distance"] / 1609.344
    duration_hours = summary["duration"] / 3600.0

    # Leaflet expects [lat, lon]
    coords = feature["geometry"]["coordinates"]
    latlngs = [[c[1], c[0]] for c in coords]

    return {
        "geometry": {
            "type": "LineString",
            "coordinates": latlngs,
        },
        "waypoints": [
            {
                "name": wp.get("name", ""),
                "label": wp.get("label", ""),
                "lat": wp["lat"],
                "lon": wp["lon"],
            }
            for wp in waypoints
        ],
        "distance_miles": round(distance_miles, 1),
        "duration_hours": round(duration_hours, 2),
        "distance_meters": summary["distance"],
        "duration_seconds": summary["duration"],
    }


def plan_route(
    current_location: str,
    pickup_location: str,
    dropoff_location: str,
) -> dict[str, Any]:
    """Geocode all stops and build a current → pickup → dropoff route."""
    current = geocode(current_location)
    pickup = geocode(pickup_location)
    dropoff = geocode(dropoff_location)

    route = get_route([current, pickup, dropoff])

    # Segment distances via separate legs for schedule timing
    to_pickup = get_route([current, pickup])
    to_dropoff = get_route([pickup, dropoff])

    return {
        "route": route,
        "legs": {
            "to_pickup": {
                "distance_miles": to_pickup["distance_miles"],
                "duration_hours": to_pickup["duration_hours"],
            },
            "to_dropoff": {
                "distance_miles": to_dropoff["distance_miles"],
                "duration_hours": to_dropoff["duration_hours"],
            },
        },
        "locations": {
            "current": current,
            "pickup": pickup,
            "dropoff": dropoff,
        },
    }
