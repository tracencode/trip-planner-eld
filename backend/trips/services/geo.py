"""Interpolate geographic points along a route polyline."""
from __future__ import annotations

import math
from typing import Any


def _haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3958.8  # Earth radius miles
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def build_route_mileposts(latlngs: list[list[float]]) -> list[dict[str, float]]:
    """
    Build cumulative mile markers along [lat, lon] coordinates.
    Returns [{lat, lon, miles}, ...] including start at 0.
    """
    if not latlngs:
        return []

    posts = [{"lat": latlngs[0][0], "lon": latlngs[0][1], "miles": 0.0}]
    total = 0.0
    for i in range(1, len(latlngs)):
        lat1, lon1 = latlngs[i - 1]
        lat2, lon2 = latlngs[i]
        total += _haversine_miles(lat1, lon1, lat2, lon2)
        posts.append({"lat": lat2, "lon": lon2, "miles": total})
    return posts


def point_at_miles(
    mileposts: list[dict[str, float]],
    target_miles: float,
) -> dict[str, float] | None:
    """Return interpolated {lat, lon} at a distance along the route."""
    if not mileposts:
        return None

    target = max(0.0, min(target_miles, mileposts[-1]["miles"]))

    if target <= 0:
        return {"lat": mileposts[0]["lat"], "lon": mileposts[0]["lon"]}

    for i in range(1, len(mileposts)):
        prev, curr = mileposts[i - 1], mileposts[i]
        if curr["miles"] >= target:
            span = curr["miles"] - prev["miles"]
            t = 0.0 if span <= 0 else (target - prev["miles"]) / span
            return {
                "lat": prev["lat"] + t * (curr["lat"] - prev["lat"]),
                "lon": prev["lon"] + t * (curr["lon"] - prev["lon"]),
            }

    last = mileposts[-1]
    return {"lat": last["lat"], "lon": last["lon"]}


def attach_stop_coordinates(
    schedule: list[dict[str, Any]],
    route_latlngs: list[list[float]],
) -> list[dict[str, Any]]:
    """
    Attach lat/lon to schedule events that should appear on the map
    (fuel, break, rest, pickup, dropoff, start, end) using miles_along_route.
    """
    mileposts = build_route_mileposts(route_latlngs)
    map_types = {"start", "fuel", "break", "rest", "pickup", "dropoff", "arrive_pickup", "arrive_dropoff", "end"}
    stops: list[dict[str, Any]] = []

    for event in schedule:
        if event.get("type") not in map_types:
            continue
        miles = float(event.get("miles_along_route") or 0)
        point = point_at_miles(mileposts, miles)
        if not point:
            continue
        stops.append(
            {
                "type": event["type"],
                "label": event.get("description") or event["type"],
                "time": event.get("time"),
                "day": event.get("day"),
                "date": event.get("date"),
                "duration_hours": event.get("duration_hours", 0),
                "miles_along_route": miles,
                "lat": round(point["lat"], 5),
                "lon": round(point["lon"], 5),
            }
        )
    return stops
