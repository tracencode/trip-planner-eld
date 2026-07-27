"""
Simple HOS schedule generator.

Rules implemented:
- Max driving per day: 11 hours
- Max duty window: 14 hours
- 30-minute break after every 8 hours of cumulative driving
- 10-hour overnight rest after 11 driving hours OR 14 duty hours
- Fuel stop every 1000 miles (30 minutes)
- Pickup: 1 hour on-duty
- Dropoff: 1 hour on-duty
- 70-hour / 8-day cycle (on-duty + driving consumes cycle)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


MAX_DRIVING_HOURS = 11.0
MAX_DUTY_HOURS = 14.0
BREAK_AFTER_DRIVING = 8.0
BREAK_DURATION_HOURS = 0.5
REST_DURATION_HOURS = 10.0
FUEL_EVERY_MILES = 1000.0
FUEL_STOP_HOURS = 0.5
PICKUP_HOURS = 1.0
DROPOFF_HOURS = 1.0
DEFAULT_START_HOUR = 8
CYCLE_LIMIT_HOURS = 70.0


@dataclass
class DayState:
    driving_hours: float = 0.0
    duty_hours: float = 0.0
    driving_since_break: float = 0.0
    miles_since_fuel: float = 0.0


@dataclass
class ScheduleBuilder:
    current_time: datetime
    cycle_remaining: float
    day: int = 1
    state: DayState = field(default_factory=DayState)
    cumulative_miles: float = 0.0
    cycle_consumed: float = 0.0
    cycle_exhausted: bool = False
    events: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, int] = field(
        default_factory=lambda: {
            "fuel_stops": 0,
            "breaks": 0,
            "rest_stops": 0,
        }
    )

    def _fmt(self, dt: datetime | None = None) -> str:
        return (dt or self.current_time).strftime("%H:%M")

    def _date(self, dt: datetime | None = None) -> str:
        return (dt or self.current_time).strftime("%Y-%m-%d")

    def add_event(
        self,
        event_type: str,
        description: str,
        duration_hours: float = 0.0,
        status: str = "on_duty",
        miles: float = 0.0,
        consume_cycle: bool = False,
    ) -> None:
        start = self.current_time
        end = start + timedelta(hours=duration_hours) if duration_hours else start
        self.events.append(
            {
                "day": self.day,
                "time": self._fmt(start),
                "end_time": self._fmt(end) if duration_hours else self._fmt(start),
                "date": self._date(start),
                "type": event_type,
                "description": description,
                "duration_hours": round(duration_hours, 2),
                "status": status,
                "miles": round(miles, 1),
                "miles_along_route": round(self.cumulative_miles, 1),
            }
        )
        if duration_hours:
            self.current_time = end
        if consume_cycle and duration_hours > 0:
            used = min(duration_hours, max(0.0, self.cycle_remaining))
            self.cycle_remaining = max(0.0, self.cycle_remaining - duration_hours)
            self.cycle_consumed += duration_hours
            if self.cycle_remaining <= 1e-6:
                self.cycle_exhausted = True
            # silence unused
            _ = used

    def needs_rest(self) -> bool:
        return (
            self.state.driving_hours >= MAX_DRIVING_HOURS - 1e-6
            or self.state.duty_hours >= MAX_DUTY_HOURS - 1e-6
        )

    def insert_rest(self, reason: str) -> None:
        self.add_event(
            "rest",
            f"10-hour overnight rest ({reason})",
            REST_DURATION_HOURS,
            status="off_duty",
        )
        self.summary["rest_stops"] += 1
        self.day += 1
        self.state = DayState(miles_since_fuel=self.state.miles_since_fuel)

    def insert_break(self) -> None:
        self.add_event(
            "break",
            "30-minute break (8 hours cumulative driving)",
            BREAK_DURATION_HOURS,
            status="off_duty",
        )
        self.summary["breaks"] += 1
        self.state.driving_since_break = 0.0
        # Break sits in the duty window clock (simplified HOS)
        self.state.duty_hours += BREAK_DURATION_HOURS

    def insert_fuel(self) -> None:
        self.add_event(
            "fuel",
            "Fuel stop",
            FUEL_STOP_HOURS,
            status="on_duty",
            consume_cycle=True,
        )
        self.summary["fuel_stops"] += 1
        self.state.miles_since_fuel = 0.0
        self.state.duty_hours += FUEL_STOP_HOURS
        if self.needs_rest():
            self.insert_rest("14-hour duty limit after fuel stop")

    def add_on_duty(self, event_type: str, description: str, hours: float) -> None:
        self.add_event(
            event_type,
            description,
            hours,
            status="on_duty",
            consume_cycle=True,
        )
        self.state.duty_hours += hours
        if self.needs_rest():
            self.insert_rest("14-hour duty limit")

    def drive_segment(self, total_hours: float, total_miles: float, label: str) -> None:
        """Drive a segment, inserting breaks/fuel/rest as limits are hit."""
        if total_hours <= 0:
            return

        mph = total_miles / total_hours if total_hours > 0 else 55.0
        remaining_hours = total_hours
        segment_started = False

        while remaining_hours > 1e-6:
            if self.needs_rest():
                reason = (
                    "11-hour driving limit"
                    if self.state.driving_hours >= MAX_DRIVING_HOURS - 1e-6
                    else "14-hour duty limit"
                )
                self.insert_rest(reason)
                segment_started = False

            # Cycle exhausted: rest resets daily clocks only; trip continues with a note
            if self.cycle_remaining <= 1e-6:
                if not any(
                    e["type"] == "cycle_warning"
                    for e in self.events
                    if e["day"] == self.day
                ):
                    self.add_event(
                        "cycle_warning",
                        "70-hour cycle limit reached — continuing after rest (34h restart not simulated)",
                        0,
                        status="off_duty",
                    )
                if self.state.driving_hours > 0 or self.state.duty_hours > 0:
                    self.insert_rest("70-hour cycle limit")
                    segment_started = False

            drive_room = MAX_DRIVING_HOURS - self.state.driving_hours
            duty_room = MAX_DUTY_HOURS - self.state.duty_hours
            break_room = BREAK_AFTER_DRIVING - self.state.driving_since_break
            fuel_miles_room = FUEL_EVERY_MILES - self.state.miles_since_fuel
            fuel_hours_room = fuel_miles_room / mph if mph > 0 else remaining_hours
            # Soft-cap by cycle when remaining; once exhausted allow progress so trip completes
            cycle_room = (
                self.cycle_remaining
                if self.cycle_remaining > 1e-6
                else remaining_hours
            )

            chunk = min(
                remaining_hours,
                drive_room,
                duty_room,
                break_room,
                fuel_hours_room,
                cycle_room,
            )

            if chunk < 1e-4:
                if self.state.driving_since_break >= BREAK_AFTER_DRIVING - 1e-6:
                    self.insert_break()
                    segment_started = False
                    continue
                if self.state.miles_since_fuel >= FUEL_EVERY_MILES - 1e-3:
                    self.insert_fuel()
                    segment_started = False
                    continue
                if self.needs_rest():
                    continue
                if self.cycle_remaining <= 1e-6:
                    self.insert_rest("70-hour cycle limit")
                    segment_started = False
                    continue
                chunk = remaining_hours

            chunk_miles = mph * chunk

            if not segment_started:
                self.add_event(
                    "driving",
                    f"Driving — {label}",
                    0,
                    status="driving",
                )
                segment_started = True

            self.current_time += timedelta(hours=chunk)
            self.events[-1]["end_time"] = self._fmt()
            self.events[-1]["duration_hours"] = round(
                self.events[-1]["duration_hours"] + chunk, 2
            )
            self.events[-1]["miles"] = round(self.events[-1]["miles"] + chunk_miles, 1)
            self.cumulative_miles += chunk_miles
            self.events[-1]["miles_along_route"] = round(self.cumulative_miles, 1)

            self.state.driving_hours += chunk
            self.state.duty_hours += chunk
            self.state.driving_since_break += chunk
            self.state.miles_since_fuel += chunk_miles
            self.cycle_remaining = max(0.0, self.cycle_remaining - chunk)
            self.cycle_consumed += chunk
            if self.cycle_remaining <= 1e-6:
                self.cycle_exhausted = True

            remaining_hours -= chunk

            if remaining_hours <= 1e-6:
                break

            if self.state.driving_since_break >= BREAK_AFTER_DRIVING - 1e-6:
                self.insert_break()
                segment_started = False
                continue

            if self.state.miles_since_fuel >= FUEL_EVERY_MILES - 1e-3:
                self.insert_fuel()
                segment_started = False
                continue

            if self.needs_rest():
                reason = (
                    "11-hour driving limit"
                    if self.state.driving_hours >= MAX_DRIVING_HOURS - 1e-6
                    else "14-hour duty limit"
                )
                self.insert_rest(reason)
                segment_started = False


def generate_schedule(
    to_pickup_hours: float,
    to_pickup_miles: float,
    to_dropoff_hours: float,
    to_dropoff_miles: float,
    current_cycle_hours: float = 0.0,
    start_time: datetime | None = None,
) -> dict[str, Any]:
    """Build a trip schedule from current → pickup → dropoff."""
    if start_time is None:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        start_time = today + timedelta(days=1, hours=DEFAULT_START_HOUR)

    cycle_remaining = max(0.0, CYCLE_LIMIT_HOURS - current_cycle_hours)
    builder = ScheduleBuilder(
        current_time=start_time,
        cycle_remaining=cycle_remaining,
    )

    builder.add_event("start", "Start trip", 0, status="on_duty")

    builder.drive_segment(to_pickup_hours, to_pickup_miles, "to pickup")

    builder.add_event("arrive_pickup", "Arrive at pickup", 0, status="on_duty")
    builder.add_on_duty("pickup", "Pickup (1 hour)", PICKUP_HOURS)

    builder.drive_segment(to_dropoff_hours, to_dropoff_miles, "to dropoff")

    builder.add_event("arrive_dropoff", "Arrive at dropoff", 0, status="on_duty")
    builder.add_on_duty("dropoff", "Dropoff (1 hour)", DROPOFF_HOURS)

    builder.add_event("end", "End trip", 0, status="off_duty")

    total_miles = to_pickup_miles + to_dropoff_miles
    total_driving = to_pickup_hours + to_dropoff_hours
    final_cycle_used = round(current_cycle_hours + builder.cycle_consumed, 2)

    return {
        "schedule": builder.events,
        "summary": {
            "total_miles": round(total_miles, 1),
            "total_driving_hours": round(total_driving, 2),
            "fuel_stops": builder.summary["fuel_stops"],
            "breaks": builder.summary["breaks"],
            "rest_stops": builder.summary["rest_stops"],
            "days": builder.day,
            "cycle_hours_used": final_cycle_used,
            "cycle_hours_remaining": round(max(0.0, CYCLE_LIMIT_HOURS - final_cycle_used), 2),
            "cycle_limit": CYCLE_LIMIT_HOURS,
            "cycle_exhausted": builder.cycle_exhausted,
            "start_time": start_time.isoformat(),
            "end_time": builder.current_time.isoformat(),
        },
    }
