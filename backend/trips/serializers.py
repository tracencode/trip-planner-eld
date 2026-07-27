from rest_framework import serializers


class PlanTripSerializer(serializers.Serializer):
    current_location = serializers.CharField(max_length=255, trim_whitespace=True)
    pickup_location = serializers.CharField(max_length=255, trim_whitespace=True)
    dropoff_location = serializers.CharField(max_length=255, trim_whitespace=True)
    current_cycle_hours = serializers.FloatField(min_value=0, max_value=70)

    def validate_current_location(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Current location is required.")
        return value.strip()

    def validate_pickup_location(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Pickup location is required.")
        return value.strip()

    def validate_dropoff_location(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Dropoff location is required.")
        return value.strip()
