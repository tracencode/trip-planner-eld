"""API views for trip planning."""
from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from trips.serializers import PlanTripSerializer
from trips.services.geo import attach_stop_coordinates
from trips.services.log_generator import generate_log_images
from trips.services.routing import RoutingError, plan_route
from trips.services.schedule import generate_schedule

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    """Simple health check for Render."""

    authentication_classes = []
    permission_classes = []

    def get(self, request: Request) -> Response:
        return Response({"status": "ok"})


class PlanTripView(APIView):
    """
    POST /api/plan-trip/

    Geocode locations, compute route, generate HOS schedule and daily log sheets.
    """

    authentication_classes = []
    permission_classes = []

    def post(self, request: Request) -> Response:
        serializer = PlanTripSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            routing = plan_route(
                data["current_location"],
                data["pickup_location"],
                data["dropoff_location"],
            )
        except RoutingError as exc:
            logger.exception("Routing error")
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        legs = routing["legs"]
        schedule_result = generate_schedule(
            to_pickup_hours=legs["to_pickup"]["duration_hours"],
            to_pickup_miles=legs["to_pickup"]["distance_miles"],
            to_dropoff_hours=legs["to_dropoff"]["duration_hours"],
            to_dropoff_miles=legs["to_dropoff"]["distance_miles"],
            current_cycle_hours=data["current_cycle_hours"],
        )

        route = routing["route"]
        latlngs = route["geometry"]["coordinates"]
        map_stops = attach_stop_coordinates(schedule_result["schedule"], latlngs)
        locations = routing["locations"]
        log_images = generate_log_images(
            schedule_result["schedule"],
            from_location=locations["current"].get("label")
            or data["current_location"],
            to_location=locations["dropoff"].get("label")
            or data["dropoff_location"],
            cycle_hours_used=schedule_result["summary"]["cycle_hours_used"],
            cycle_hours_remaining=schedule_result["summary"]["cycle_hours_remaining"],
        )
        summary = schedule_result["summary"]

        return Response(
            {
                "route": {
                    "geometry": route["geometry"],
                    "waypoints": route["waypoints"],
                },
                "distance": route["distance_miles"],
                "duration": route["duration_hours"],
                "schedule": schedule_result["schedule"],
                "map_stops": map_stops,
                "log_images": [img["url"] for img in log_images],
                "log_sheets": log_images,
                "summary": {
                    "distance_miles": summary["total_miles"],
                    "driving_hours": summary["total_driving_hours"],
                    "fuel_stops": summary["fuel_stops"],
                    "breaks": summary["breaks"],
                    "rest_stops": summary["rest_stops"],
                    "days": summary["days"],
                    "cycle_hours_used": summary["cycle_hours_used"],
                    "cycle_hours_remaining": summary["cycle_hours_remaining"],
                    "cycle_limit": summary["cycle_limit"],
                    "cycle_exhausted": summary["cycle_exhausted"],
                    "current_cycle_input": data["current_cycle_hours"],
                },
                "locations": routing["locations"],
            }
        )
