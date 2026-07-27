from django.test import SimpleTestCase

from trips.services.schedule import generate_schedule


class ScheduleGenerationTests(SimpleTestCase):
    def test_short_trip_schedule(self):
        """Short trip: pickup + dropoff with no rest needed."""
        result = generate_schedule(
            to_pickup_hours=2.0,
            to_pickup_miles=100.0,
            to_dropoff_hours=3.0,
            to_dropoff_miles=150.0,
            current_cycle_hours=10.0,
        )
        types = [e["type"] for e in result["schedule"]]
        self.assertIn("start", types)
        self.assertIn("pickup", types)
        self.assertIn("dropoff", types)
        self.assertIn("end", types)
        self.assertEqual(result["summary"]["breaks"], 0)
        self.assertEqual(result["summary"]["rest_stops"], 0)

    def test_break_after_eight_hours(self):
        """Driving past 8 hours should insert a 30-minute break."""
        result = generate_schedule(
            to_pickup_hours=1.0,
            to_pickup_miles=50.0,
            to_dropoff_hours=9.0,
            to_dropoff_miles=450.0,
            current_cycle_hours=0.0,
        )
        self.assertGreaterEqual(result["summary"]["breaks"], 1)
        self.assertTrue(any(e["type"] == "break" for e in result["schedule"]))

    def test_rest_after_eleven_driving(self):
        """Exceeding 11 driving hours should insert overnight rest."""
        result = generate_schedule(
            to_pickup_hours=4.0,
            to_pickup_miles=200.0,
            to_dropoff_hours=10.0,
            to_dropoff_miles=550.0,
            current_cycle_hours=0.0,
        )
        self.assertGreaterEqual(result["summary"]["rest_stops"], 1)
        self.assertTrue(any(e["type"] == "rest" for e in result["schedule"]))

    def test_fuel_every_thousand_miles(self):
        """Trips over 1000 miles should include a fuel stop."""
        result = generate_schedule(
            to_pickup_hours=2.0,
            to_pickup_miles=100.0,
            to_dropoff_hours=18.0,
            to_dropoff_miles=1100.0,
            current_cycle_hours=0.0,
        )
        self.assertGreaterEqual(result["summary"]["fuel_stops"], 1)

    def test_cycle_tracking_70_hour(self):
        """Cycle hours should be consumed and remaining reported against 70h."""
        result = generate_schedule(
            to_pickup_hours=2.0,
            to_pickup_miles=100.0,
            to_dropoff_hours=3.0,
            to_dropoff_miles=150.0,
            current_cycle_hours=40.0,
        )
        self.assertEqual(result["summary"]["cycle_limit"], 70.0)
        self.assertGreater(result["summary"]["cycle_hours_used"], 40.0)
        self.assertLess(result["summary"]["cycle_hours_remaining"], 30.0)

    def test_events_include_miles_along_route(self):
        """Stop events should carry miles_along_route for map plotting."""
        result = generate_schedule(
            to_pickup_hours=2.0,
            to_pickup_miles=100.0,
            to_dropoff_hours=3.0,
            to_dropoff_miles=150.0,
            current_cycle_hours=0.0,
        )
        pickup = next(e for e in result["schedule"] if e["type"] == "pickup")
        self.assertAlmostEqual(pickup["miles_along_route"], 100.0, places=0)
