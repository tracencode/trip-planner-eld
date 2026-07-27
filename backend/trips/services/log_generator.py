"""
Generate daily driver log sheets by drawing on the blank FMCSA-style form.

Uses trips/assets/blank_log.png as the template and overlays:
- date / from / to
- total miles
- duty-status graph lines (Off Duty / Sleeper / Driving / On Duty)
- total hours per status
- remarks
- simple 70hr/8day recap values
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont


# --- Template geometry (base blank is 513×518; we scale up for clarity) ---
BLANK_PATH = Path(__file__).resolve().parent.parent / "assets" / "blank_log.png"
SCALE = 3

# Coordinates are in *base* (1×) pixels; multiplied by SCALE when drawing.
GRAPH_LEFT = 97.0
GRAPH_RIGHT = 445.0
HOURS = 24

# Horizontal separators of the 4 duty rows (from calibration)
ROW_BOUNDS = [184.0, 201.0, 218.0, 235.0, 252.0]
STATUS_ROWS = {
    "off_duty": 0,
    "sleeper": 1,
    "driving": 2,
    "on_duty": 3,
}


def _s(v: float) -> int:
    return int(round(v * SCALE))


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    size = max(10, int(size * SCALE / 2.2))
    for name in (
        "/System/Library/Fonts/Supplemental/Courier New.ttf",
        "/System/Library/Fonts/Courier.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _hour_x(hour: float) -> float:
    return GRAPH_LEFT + (hour / HOURS) * (GRAPH_RIGHT - GRAPH_LEFT)


def _row_y(status: str) -> float:
    idx = STATUS_ROWS.get(status, 0)
    return (ROW_BOUNDS[idx] + ROW_BOUNDS[idx + 1]) / 2.0


def _parse_events_by_day(schedule: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    by_day: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for event in schedule:
        by_day[event["day"]].append(event)
    return dict(by_day)


def _build_status_segments(
    day_events: list[dict[str, Any]],
    day_start: datetime,
) -> list[tuple[float, float, str]]:
    segments: list[tuple[float, float, str]] = []
    day_end = day_start + timedelta(hours=24)

    for event in day_events:
        duration = float(event.get("duration_hours") or 0)
        if duration <= 0:
            continue
        try:
            start_dt = datetime.strptime(
                f"{event['date']} {event['time']}", "%Y-%m-%d %H:%M"
            )
        except ValueError:
            continue

        end_dt = start_dt + timedelta(hours=duration)
        status = event.get("status", "on_duty")
        seg_start = max(start_dt, day_start)
        seg_end = min(end_dt, day_end)
        if seg_end <= seg_start:
            continue

        start_h = (seg_start - day_start).total_seconds() / 3600
        end_h = (seg_end - day_start).total_seconds() / 3600
        segments.append((start_h, end_h, status))

    return segments


def _day_totals(day_events: list[dict[str, Any]]) -> dict[str, float]:
    miles = 0.0
    hours = {"off_duty": 0.0, "sleeper": 0.0, "driving": 0.0, "on_duty": 0.0}
    for e in day_events:
        miles += float(e.get("miles") or 0)
        dur = float(e.get("duration_hours") or 0)
        status = e.get("status")
        if status in hours:
            hours[status] += dur
    # Remaining time in the calendar day is off-duty for the sheet total
    accounted = sum(hours.values())
    if accounted < 24:
        hours["off_duty"] += 24 - accounted
    return {
        "miles": round(miles, 1),
        "off_duty": round(hours["off_duty"], 2),
        "sleeper": round(hours["sleeper"], 2),
        "driving": round(hours["driving"], 2),
        "on_duty": round(hours["on_duty"], 2),
        "duty_hours": round(hours["driving"] + hours["on_duty"], 2),
    }


def _remarks(day_events: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for e in day_events:
        if e["type"] in (
            "start",
            "break",
            "rest",
            "fuel",
            "pickup",
            "dropoff",
            "arrive_pickup",
            "arrive_dropoff",
            "cycle_warning",
            "end",
        ):
            lines.append(f"{e['time']} {e['description']}")
    return lines[:10]


def _load_blank() -> Image.Image:
    if not BLANK_PATH.exists():
        raise FileNotFoundError(f"Blank log template missing: {BLANK_PATH}")
    base = Image.open(BLANK_PATH).convert("RGBA")
    # Upscale for sharper handwriting-style overlays
    return base.resize(
        (base.width * SCALE, base.height * SCALE),
        Image.Resampling.LANCZOS,
    )


def draw_log_sheet(
    day: int,
    day_date: str,
    segments: list[tuple[float, float, str]],
    totals: dict[str, float],
    remarks: list[str],
    from_location: str = "",
    to_location: str = "",
    cycle_used: float = 0.0,
    cycle_remaining: float = 70.0,
) -> Image.Image:
    img = _load_blank()
    draw = ImageDraw.Draw(img)

    ink = (15, 40, 120)  # blue pen look
    ink_dark = (20, 20, 20)
    font_sm = _font(11)
    font_md = _font(13)
    font_lg = _font(15)

    # --- Header fields ---
    try:
        dt = datetime.strptime(day_date, "%Y-%m-%d")
        month, day_n, year = f"{dt.month:02d}", f"{dt.day:02d}", str(dt.year)
    except ValueError:
        month, day_n, year = "", "", day_date

    # Date: month / day / year (top right area of form)
    draw.text((_s(268), _s(36)), month, fill=ink, font=font_md)
    draw.text((_s(312), _s(36)), day_n, fill=ink, font=font_md)
    draw.text((_s(350), _s(36)), year, fill=ink, font=font_md)

    # From / To
    draw.text((_s(55), _s(58)), (from_location or "")[:42], fill=ink, font=font_sm)
    draw.text((_s(55), _s(74)), (to_location or "")[:42], fill=ink, font=font_sm)

    # Miles boxes
    draw.text((_s(95), _s(100)), str(totals["miles"]), fill=ink, font=font_lg)
    draw.text((_s(95), _s(122)), str(totals["miles"]), fill=ink, font=font_lg)

    # Carrier / vehicle placeholders (assessment-friendly)
    draw.text((_s(210), _s(95)), "Trip Planner Carrier", fill=ink, font=font_sm)
    draw.text((_s(210), _s(110)), "Main Office — Assessment MVP", fill=ink, font=font_sm)
    draw.text((_s(210), _s(125)), "Home Terminal — Local", fill=ink, font=font_sm)
    draw.text((_s(390), _s(108)), "TRUCK-01", fill=ink, font=font_md)

    # --- Duty graph lines ---
    sorted_segs = sorted(segments, key=lambda s: s[0])
    last_end = 0.0
    last_status = "off_duty"
    line_w = max(3, SCALE)

    def draw_status_line(start_h: float, end_h: float, status: str) -> None:
        if end_h <= start_h:
            return
        y = _s(_row_y(status))
        x1 = _s(_hour_x(start_h))
        x2 = _s(_hour_x(end_h))
        draw.line([(x1, y), (x2, y)], fill=ink_dark, width=line_w)
        r = max(2, SCALE)
        draw.ellipse([x1 - r, y - r, x1 + r, y + r], fill=ink_dark)
        draw.ellipse([x2 - r, y - r, x2 + r, y + r], fill=ink_dark)

    def draw_connector(at_h: float, from_status: str, to_status: str) -> None:
        if from_status == to_status:
            return
        x = _s(_hour_x(at_h))
        y1 = _s(_row_y(from_status))
        y2 = _s(_row_y(to_status))
        draw.line([(x, y1), (x, y2)], fill=ink_dark, width=max(2, SCALE - 1))

    for start_h, end_h, status in sorted_segs:
        if start_h > last_end + 0.01:
            draw_status_line(last_end, start_h, "off_duty")
            draw_connector(last_end, last_status, "off_duty")
            last_status = "off_duty"
        draw_connector(start_h, last_status, status)
        draw_status_line(start_h, end_h, status)
        last_status = status
        last_end = end_h

    if last_end < 24:
        draw_connector(last_end, last_status, "off_duty")
        draw_status_line(last_end, 24, "off_duty")

    # --- Total hours column (right of grid) ---
    total_x = _s(455)
    for status, key in (
        ("off_duty", "off_duty"),
        ("sleeper", "sleeper"),
        ("driving", "driving"),
        ("on_duty", "on_duty"),
    ):
        y = _s(_row_y(status) - 4)
        draw.text((total_x, y), f"{totals[key]:.1f}", fill=ink, font=font_sm)

    # --- Remarks ---
    ry = _s(268)
    rx = _s(40)
    for line in remarks:
        draw.text((rx, ry), line[:70], fill=ink, font=font_sm)
        ry += _s(11)
        if ry > _s(360):
            break

    draw.text((_s(300), _s(300)), "Shipper & Commodity: General Freight", fill=ink, font=font_sm)
    draw.text((_s(300), _s(315)), f"Day {day} log sheet", fill=ink, font=font_sm)

    # --- Recap (70 hour / 8 day) ---
    # A ≈ cycle used today snapshot, B ≈ remaining
    draw.text((_s(175), _s(430)), f"{cycle_used:.1f}", fill=ink, font=font_md)
    draw.text((_s(175), _s(455)), f"{max(0.0, cycle_remaining):.1f}", fill=ink, font=font_md)
    draw.text((_s(175), _s(480)), f"{cycle_used:.1f}", fill=ink, font=font_md)

    return img.convert("RGB")


def generate_log_images(
    schedule: list[dict[str, Any]],
    from_location: str = "",
    to_location: str = "",
    cycle_hours_used: float = 0.0,
    cycle_hours_remaining: float = 70.0,
) -> list[dict[str, str]]:
    """Generate one PNG per day by drawing on the blank log template."""
    media_logs = Path(settings.MEDIA_ROOT) / "logs"
    media_logs.mkdir(parents=True, exist_ok=True)

    by_day = _parse_events_by_day(schedule)
    results: list[dict[str, str]] = []
    trip_id = uuid.uuid4().hex[:10]
    all_events = list(schedule)

    for day in sorted(by_day.keys()):
        events = by_day[day]
        day_date = events[0]["date"]
        day_start = datetime.strptime(day_date, "%Y-%m-%d")

        overlapping = []
        for e in all_events:
            dur = float(e.get("duration_hours") or 0)
            if dur <= 0:
                continue
            try:
                start_dt = datetime.strptime(f"{e['date']} {e['time']}", "%Y-%m-%d %H:%M")
            except ValueError:
                continue
            end_dt = start_dt + timedelta(hours=dur)
            day_end = day_start + timedelta(hours=24)
            if start_dt < day_end and end_dt > day_start:
                overlapping.append(e)

        # Per-day from/to: start day uses current→pickup-ish; later days dropoff
        day_from = from_location
        day_to = to_location
        if day == 1 and from_location:
            day_from = from_location
        segments = _build_status_segments(overlapping, day_start)
        totals = _day_totals(events)
        remarks = _remarks(events)

        img = draw_log_sheet(
            day=day,
            day_date=day_date,
            segments=segments,
            totals=totals,
            remarks=remarks,
            from_location=day_from,
            to_location=day_to,
            cycle_used=cycle_hours_used,
            cycle_remaining=cycle_hours_remaining,
        )

        filename = f"log_{trip_id}_day{day}.png"
        path = media_logs / filename
        img.save(path, "PNG")

        url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/media/logs/{filename}"
        results.append(
            {
                "day": day,
                "date": day_date,
                "url": url,
                "filename": filename,
            }
        )

    return results
