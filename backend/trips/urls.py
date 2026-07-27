from django.urls import path

from trips.views import HealthCheckView, PlanTripView

urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("plan-trip/", PlanTripView.as_view(), name="plan-trip"),
]
