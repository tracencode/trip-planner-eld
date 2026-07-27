"""
Generate Drivers Daily Log sheets by drawing an FMCSA-style template from scratch.

Creates a form similar to the official blank paper log (header, duty grid with
15-minute ticks, remarks, shipping docs, and 70hr/8day recap), then fills it
with trip schedule data.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont


WIDTH = 1700
HEIGHT = 2200
MARGIN = 48
INK = (20, 20, 20)
GRID = (40, 40, 40)
LIGHT = (120, 120, 120)
FILL_BLUE = (20, 55, 140)
WHITE = (255, 255, 255)
HEADER_BG = (15, 15, 15)

STATUS_ORDER = [
    ("off_duty", "1. Off Duty"),
    ("sleeper", "2. Sleeper Berth"),
    ("driving", "3. Driving"),
    ("on_duty", "4. On Duty (not driving)"),
]


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        (
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
            if bold
            else "/System/Library/Fonts/Supplemental/Arial.ttf"
        ),
        (
            "/System/Library/Fonts/Helvetica.ttc"
        ),
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ),
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    )
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


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
            lines.append(f"{e['time']} — {e['description']}")
    return lines[:12]


def _box(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], width: int = 2) -> None:
    draw.rectangle(xy, outline=INK, width=width)


def _hline(draw: ImageDraw.ImageDraw, x1: int, x2: int, y: int, width: int = 1, fill=INK) -> None:
    draw.line([(x1, y), (x2, y)], fill=fill, width=width)


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
    img = Image.new("RGB", (WIDTH, HEIGHT), WHITE)
    draw = ImageDraw.Draw(img)

    title_f = _font(36, bold=True)
    h1 = _font(18, bold=True)
    body = _font(15)
    small = _font(12)
    tiny = _font(11)
    fill_f = _font(17, bold=True)

    left = MARGIN
    right = WIDTH - MARGIN
    y = MARGIN

    # Outer page border
    _box(draw, (MARGIN - 8, MARGIN - 8, WIDTH - MARGIN + 8, HEIGHT - MARGIN + 8), 3)

    # --- Title row ---
    draw.text((left, y), "Drivers Daily Log (24 hours)", fill=INK, font=title_f)

    try:
        dt = datetime.strptime(day_date, "%Y-%m-%d")
        month, day_n, year = f"{dt.month:02d}", f"{dt.day:02d}", str(dt.year)
    except ValueError:
        month, day_n, year = "", "", day_date

    date_x = 760
    draw.text((date_x, y + 8), "(month)", fill=LIGHT, font=tiny)
    draw.text((date_x + 90, y + 8), "(day)", fill=LIGHT, font=tiny)
    draw.text((date_x + 160, y + 8), "(year)", fill=LIGHT, font=tiny)
    _hline(draw, date_x, date_x + 70, y + 42, 1)
    _hline(draw, date_x + 85, date_x + 145, y + 42, 1)
    _hline(draw, date_x + 160, date_x + 250, y + 42, 1)
    draw.text((date_x + 18, y + 18), month, fill=FILL_BLUE, font=fill_f)
    draw.text((date_x + 100, y + 18), day_n, fill=FILL_BLUE, font=fill_f)
    draw.text((date_x + 175, y + 18), year, fill=FILL_BLUE, font=fill_f)
    draw.text((date_x + 72, y + 22), "/", fill=INK, font=body)
    draw.text((date_x + 148, y + 22), "/", fill=INK, font=body)

    draw.text(
        (1150, y + 4),
        "Original — File at home terminal.\nDuplicate — Driver retains in his/her\npossession for 8 days.",
        fill=INK,
        font=tiny,
    )

    y += 70
    # From / To
    draw.text((left, y), "From:", fill=INK, font=body)
    _hline(draw, left + 70, right, y + 18, 1)
    draw.text((left + 80, y - 2), (from_location or "")[:70], fill=FILL_BLUE, font=fill_f)
    y += 36
    draw.text((left, y), "To:", fill=INK, font=body)
    _hline(draw, left + 50, right, y + 18, 1)
    draw.text((left + 60, y - 2), (to_location or "")[:70], fill=FILL_BLUE, font=fill_f)

    y += 50
    # Miles + vehicle + carrier block
    box_h = 70
    miles_w = 210
    _box(draw, (left, y, left + miles_w, y + box_h))
    _box(draw, (left + miles_w, y, left + miles_w * 2, y + box_h))
    draw.text((left + 10, y + 6), "Total Miles Driving Today", fill=INK, font=tiny)
    draw.text((left + miles_w + 10, y + 6), "Total Mileage Today", fill=INK, font=tiny)
    draw.text((left + 70, y + 28), str(totals["miles"]), fill=FILL_BLUE, font=_font(28, bold=True))
    draw.text(
        (left + miles_w + 70, y + 28),
        str(totals["miles"]),
        fill=FILL_BLUE,
        font=_font(28, bold=True),
    )

    veh_top = y + box_h
    veh_h = 90
    _box(draw, (left, veh_top, left + miles_w * 2, veh_top + veh_h))
    draw.text(
        (left + 10, veh_top + 8),
        "Truck/Tractor and Trailer Numbers or License Plate(s)/State (show each unit)",
        fill=INK,
        font=tiny,
    )
    draw.text((left + 20, veh_top + 40), "TRUCK-01", fill=FILL_BLUE, font=fill_f)

    carrier_x = left + miles_w * 2 + 24
    cy = y + 8
    for label, value in (
        ("Name of Carrier or Carriers", "Trip Planner Carrier"),
        ("Main Office Address", "Assessment MVP — Main Office"),
        ("Home Terminal Address", "Home Terminal — Local"),
    ):
        draw.text((carrier_x, cy), label, fill=LIGHT, font=tiny)
        _hline(draw, carrier_x, right, cy + 34, 1)
        draw.text((carrier_x, cy + 12), value, fill=FILL_BLUE, font=body)
        cy += 52

    y = veh_top + veh_h + 28

    # --- Duty status grid ---
    label_w = 210
    total_w = 110
    graph_left = left + label_w
    graph_right = right - total_w
    graph_width = graph_right - graph_left
    row_h = 78
    header_h = 42
    graph_top = y + header_h
    graph_bottom = graph_top + row_h * 4

    # Hour header bar
    draw.rectangle([graph_left, y, graph_right, graph_top], fill=HEADER_BG)
    hour_labels = (
        ["Mid\nnight"]
        + [str(i) for i in range(1, 12)]
        + ["Noon"]
        + [str(i) for i in range(1, 12)]
        + ["Mid\nnight"]
    )
    # 25 labels for 24 hour boundaries (0..24)
    for i, label in enumerate(hour_labels):
        x = graph_left + int(i / 24 * graph_width)
        # center label in hour cell for 0-23, last at end
        if i < 24:
            cx = graph_left + int((i + 0.5) / 24 * graph_width)
        else:
            cx = graph_right - 8
        # Use condensed labels on the black bar
        if i == 0:
            draw.text((graph_left + 4, y + 6), "Mid-night", fill=WHITE, font=tiny)
        elif i == 12:
            draw.text((cx - 16, y + 12), "Noon", fill=WHITE, font=tiny)
        elif i == 24:
            draw.text((graph_right - 58, y + 6), "Mid-night", fill=WHITE, font=tiny)
        elif i < 24:
            draw.text((cx - 4, y + 12), str(i if i <= 12 else i - 12), fill=WHITE, font=tiny)

    draw.text((graph_right + 12, y + 12), "Total\nHours", fill=INK, font=small)

    # Grid body
    _box(draw, (left, graph_top, right, graph_bottom), 2)
    draw.line([(graph_left, graph_top), (graph_left, graph_bottom)], fill=INK, width=2)
    draw.line([(graph_right, graph_top), (graph_right, graph_bottom)], fill=INK, width=2)

    for i, (key, label) in enumerate(STATUS_ORDER):
        top = graph_top + i * row_h
        mid = top + row_h // 2
        if i > 0:
            _hline(draw, left, right, top, 1)
        draw.text((left + 10, mid - 8), label, fill=INK, font=small)
        # midline guide for drawing
        draw.line([(graph_left, mid), (graph_right, mid)], fill=(210, 210, 210), width=1)

    # Vertical hour + quarter-hour ticks
    for h in range(25):
        x = graph_left + int(h / 24 * graph_width)
        width = 2 if h % 6 == 0 else 1
        draw.line([(x, graph_top), (x, graph_bottom)], fill=GRID if h % 6 == 0 else (180, 180, 180), width=width)
        if h < 24:
            for q in (1, 2, 3):
                qx = graph_left + int((h + q / 4) / 24 * graph_width)
                # short ticks at each row midline area
                for r in range(4):
                    ry = graph_top + r * row_h + row_h // 2
                    draw.line([(qx, ry - 8), (qx, ry + 8)], fill=(190, 190, 190), width=1)

    def hour_x(hour: float) -> int:
        return graph_left + int(max(0.0, min(24.0, hour)) / 24 * graph_width)

    def row_mid(status: str) -> int:
        idx = next(i for i, (k, _) in enumerate(STATUS_ORDER) if k == status)
        return graph_top + idx * row_h + row_h // 2

    # Draw duty lines
    sorted_segs = sorted(segments, key=lambda s: s[0])
    last_end = 0.0
    last_status = "off_duty"
    line_w = 5

    def draw_status_line(start_h: float, end_h: float, status: str) -> None:
        if end_h <= start_h + 1e-6:
            return
        y_line = row_mid(status)
        x1, x2 = hour_x(start_h), hour_x(end_h)
        draw.line([(x1, y_line), (x2, y_line)], fill=INK, width=line_w)
        r = 4
        draw.ellipse([x1 - r, y_line - r, x1 + r, y_line + r], fill=INK)
        draw.ellipse([x2 - r, y_line - r, x2 + r, y_line + r], fill=INK)

    def draw_connector(at_h: float, from_status: str, to_status: str) -> None:
        if from_status == to_status:
            return
        x = hour_x(at_h)
        draw.line(
            [(x, row_mid(from_status)), (x, row_mid(to_status))],
            fill=INK,
            width=3,
        )

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

    # Total hours column values
    for i, (key, _) in enumerate(STATUS_ORDER):
        mid = graph_top + i * row_h + row_h // 2
        draw.text(
            (graph_right + 28, mid - 10),
            f"{totals[key]:.1f}",
            fill=FILL_BLUE,
            font=fill_f,
        )

    y = graph_bottom + 24

    # --- Remarks ---
    remarks_h = 320
    _box(draw, (left, y, right, y + remarks_h), 2)
    draw.text((left + 12, y + 10), "Remarks", fill=INK, font=h1)
    ry = y + 42
    if not remarks:
        draw.text((left + 16, ry), "No special remarks for this day.", fill=LIGHT, font=body)
    else:
        for line in remarks:
            draw.text((left + 16, ry), line[:95], fill=FILL_BLUE, font=body)
            ry += 22
            if ry > y + remarks_h - 90:
                break

    # Shipping docs inside remarks box bottom
    ship_y = y + remarks_h - 70
    _hline(draw, left, right, ship_y, 1)
    draw.text((left + 12, ship_y + 8), "Shipping Documents:", fill=INK, font=small)
    draw.text((left + 200, ship_y + 8), "DVL or Manifest No. or", fill=LIGHT, font=tiny)
    _hline(draw, left + 380, right - 20, ship_y + 24, 1)
    draw.text((left + 12, ship_y + 36), "Shipper & Commodity", fill=INK, font=small)
    draw.text((left + 200, ship_y + 34), "General Freight", fill=FILL_BLUE, font=body)

    y = y + remarks_h + 12
    draw.text(
        (left, y),
        "Enter name of place you reported and where released from work and when and where each change of duty occurred. Use time standard of home terminal.",
        fill=INK,
        font=tiny,
    )

    y += 36
    # --- Recap ---
    draw.text((left, y), "Recap: Complete at end of day", fill=INK, font=h1)
    y += 28
    draw.text(
        (left, y),
        f"On duty hours today, Total lines 3 & 4:  {totals['duty_hours']:.1f}",
        fill=FILL_BLUE,
        font=body,
    )
    y += 36

    recap_top = y
    recap_h = 220
    _box(draw, (left, recap_top, right, recap_top + recap_h), 2)

    # Left labels
    draw.text((left + 12, recap_top + 20), "70 Hour / 8 Day Drivers", fill=INK, font=h1)
    draw.text((left + 12, recap_top + 120), "60 Hour / 7 Day Drivers", fill=INK, font=h1)

    # Columns A B C
    col_w = 280
    start_x = left + 320
    headers = [
        ("A", "Total hours on duty last\n7 days including today"),
        ("B", "Total hours available\ntomorrow 70 hr. minus A*"),
        ("C", "Total hours on duty last\n8 days including today"),
    ]
    values_70 = [f"{cycle_used:.1f}", f"{max(0.0, cycle_remaining):.1f}", f"{cycle_used:.1f}"]
    values_60 = ["—", "—", "—"]

    for i, ((letter, caption), val) in enumerate(zip(headers, values_70)):
        cx = start_x + i * col_w
        draw.line([(cx, recap_top), (cx, recap_top + recap_h)], fill=INK, width=1)
        draw.text((cx + 12, recap_top + 8), letter, fill=INK, font=h1)
        draw.text((cx + 40, recap_top + 10), caption, fill=LIGHT, font=tiny)
        _box(draw, (cx + 40, recap_top + 55, cx + 160, recap_top + 95), 1)
        draw.text((cx + 60, recap_top + 65), val, fill=FILL_BLUE, font=fill_f)
        # 60-hr row placeholders
        _box(draw, (cx + 40, recap_top + 150, cx + 160, recap_top + 190), 1)
        draw.text((cx + 70, recap_top + 160), values_60[i], fill=LIGHT, font=body)

    draw.text(
        (right - 320, recap_top + recap_h - 28),
        "*If you took 34 consecutive hours off duty\nyou have 60/70 hours available.",
        fill=INK,
        font=tiny,
    )

    # Footer
    draw.text(
        (left, HEIGHT - MARGIN - 10),
        f"Day {day}  ·  Generated by Trip Planner & ELD Log Generator  ·  Property-carrying 70hr/8day",
        fill=LIGHT,
        font=tiny,
    )

    return img


def generate_log_images(
    schedule: list[dict[str, Any]],
    from_location: str = "",
    to_location: str = "",
    cycle_hours_used: float = 0.0,
    cycle_hours_remaining: float = 70.0,
) -> list[dict[str, str]]:
    """Generate one filled daily-log PNG per day using a drawn template."""
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

        segments = _build_status_segments(overlapping, day_start)
        totals = _day_totals(events)
        remarks = _remarks(events)

        img = draw_log_sheet(
            day=day,
            day_date=day_date,
            segments=segments,
            totals=totals,
            remarks=remarks,
            from_location=from_location,
            to_location=to_location,
            cycle_used=cycle_hours_used,
            cycle_remaining=cycle_hours_remaining,
        )

        filename = f"log_{trip_id}_day{day}.png"
        path = media_logs / filename
        img.save(path, "PNG", optimize=True)

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
