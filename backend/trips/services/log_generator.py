"""
Generate FMCSA-style daily driver log sheet PNGs.

Draws Off Duty / Sleeper / Driving / On Duty graph lines and fills
totals (miles, driving hours, duty hours) plus remarks.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from django.conf import settings
from PIL import Image, ImageDraw, ImageFont


WIDTH = 1400
HEIGHT = 900
MARGIN_LEFT = 160
MARGIN_RIGHT = 50
GRAPH_TOP = 220
ROW_HEIGHT = 70
HOURS = 24

STATUSES = [
    ("off_duty", "1. Off Duty", 0),
    ("sleeper", "2. Sleeper Berth", 1),
    ("driving", "3. Driving", 2),
    ("on_duty", "4. On Duty (Not Driving)", 3),
]


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in (
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _hour_x(hour: float) -> float:
    graph_width = WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    return MARGIN_LEFT + (hour / HOURS) * graph_width


def _status_y(row: int) -> float:
    return GRAPH_TOP + row * ROW_HEIGHT + ROW_HEIGHT / 2


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
            # Event may span into next calendar day — clip portion on this day
            if start_dt < day_end and end_dt > day_start:
                seg_start = max(start_dt, day_start)
                seg_end = min(end_dt, day_end)
            else:
                continue
        if seg_end <= seg_start:
            continue

        start_h = (seg_start - day_start).total_seconds() / 3600
        end_h = (seg_end - day_start).total_seconds() / 3600
        segments.append((start_h, end_h, status))

    return segments


def _day_totals(day_events: list[dict[str, Any]]) -> dict[str, float]:
    miles = 0.0
    driving = 0.0
    duty = 0.0
    off_duty = 0.0
    for e in day_events:
        miles += float(e.get("miles") or 0)
        dur = float(e.get("duration_hours") or 0)
        status = e.get("status")
        if status == "driving":
            driving += dur
            duty += dur
        elif status == "on_duty":
            duty += dur
        elif status == "off_duty":
            off_duty += dur
    return {
        "miles": round(miles, 1),
        "driving_hours": round(driving, 2),
        "duty_hours": round(duty, 2),
        "off_duty_hours": round(off_duty, 2),
    }


def _remarks(day_events: list[dict[str, Any]]) -> list[str]:
    lines = []
    for e in day_events:
        if e["type"] in ("break", "rest", "fuel", "pickup", "dropoff", "cycle_warning"):
            lines.append(f"{e['time']} — {e['description']}")
    return lines[:8]


def draw_log_sheet(
    day: int,
    day_date: str,
    segments: list[tuple[float, float, str]],
    totals: dict[str, float],
    remarks: list[str],
) -> Image.Image:
    img = Image.new("RGB", (WIDTH, HEIGHT), "#fafafa")
    draw = ImageDraw.Draw(img)
    title_font = _font(26)
    label_font = _font(15)
    small_font = _font(12)
    tiny_font = _font(11)

    # Outer border (form look)
    draw.rectangle([20, 20, WIDTH - 20, HEIGHT - 20], outline="#1e293b", width=2)

    # Header
    draw.text((40, 36), "Drivers Daily Log", fill="#0f172a", font=title_font)
    draw.text(
        (40, 72),
        "(24 hours)  —  Property-Carrying  —  70 hr / 8 day",
        fill="#475569",
        font=small_font,
    )

    # Form fields row
    y = 100
    fields = [
        (40, "Date", day_date),
        (280, "Day #", str(day)),
        (400, "Total Miles Driving Today", str(totals["miles"])),
        (720, "Shipping Docs", "N/A"),
        (980, "Vehicle IDs", "TRUCK-01"),
    ]
    for x, label, value in fields:
        draw.text((x, y), label, fill="#64748b", font=tiny_font)
        draw.line([(x, y + 36), (x + 200, y + 36)], fill="#94a3b8", width=1)
        draw.text((x, y + 18), value, fill="#0f172a", font=label_font)

    # Totals boxes
    box_y = 155
    boxes = [
        ("Off Duty", f"{totals['off_duty_hours']} h"),
        ("Driving", f"{totals['driving_hours']} h"),
        ("On Duty", f"{totals['duty_hours']} h"),
        ("Total Duty", f"{totals['duty_hours']} h"),
    ]
    bx = 40
    for label, value in boxes:
        draw.rectangle([bx, box_y, bx + 150, box_y + 44], outline="#94a3b8", width=1)
        draw.text((bx + 10, box_y + 4), label, fill="#64748b", font=tiny_font)
        draw.text((bx + 10, box_y + 20), value, fill="#1e40af", font=label_font)
        bx += 165

    graph_bottom = GRAPH_TOP + len(STATUSES) * ROW_HEIGHT
    graph_right = WIDTH - MARGIN_RIGHT

    draw.rectangle(
        [MARGIN_LEFT, GRAPH_TOP, graph_right, graph_bottom],
        outline="#334155",
        width=2,
        fill="white",
    )

    for name, label, row in STATUSES:
        y_top = GRAPH_TOP + row * ROW_HEIGHT
        y_mid = _status_y(row)
        if row > 0:
            draw.line([(MARGIN_LEFT, y_top), (graph_right, y_top)], fill="#94a3b8", width=1)
        draw.text((28, y_mid - 8), label, fill="#1e293b", font=tiny_font)

    # Hour grid + noon marker
    for h in range(HOURS + 1):
        x = _hour_x(h)
        color = "#64748b" if h == 12 else "#cbd5e1"
        width = 2 if h in (0, 12, 24) else 1
        draw.line([(x, GRAPH_TOP), (x, graph_bottom)], fill=color, width=width)
        if h % 1 == 0:
            # quarter ticks mid-hour already covered by hour lines
            pass
        label = f"{h}" if h < 24 else "24"
        if h % 2 == 0:
            draw.text((x - 6, graph_bottom + 6), label, fill="#475569", font=tiny_font)

    draw.text((_hour_x(12) - 18, graph_bottom + 24), "Noon", fill="#64748b", font=tiny_font)
    draw.text((_hour_x(0) - 4, graph_bottom + 24), "Midnight", fill="#64748b", font=tiny_font)

    status_map = {s[0]: s[2] for s in STATUSES}
    colors = {
        "off_duty": "#475569",
        "sleeper": "#7c3aed",
        "driving": "#1d4ed8",
        "on_duty": "#c2410c",
    }

    last_end = 0.0
    last_row = 0
    sorted_segs = sorted(segments, key=lambda s: s[0])

    def draw_line_seg(start_h: float, end_h: float, status: str) -> int:
        row = status_map.get(status, 0)
        y = _status_y(row)
        x1 = _hour_x(start_h)
        x2 = _hour_x(end_h)
        color = colors.get(status, "#334155")
        draw.line([(x1, y), (x2, y)], fill=color, width=5)
        draw.ellipse([x1 - 3, y - 3, x1 + 3, y + 3], fill=color)
        draw.ellipse([x2 - 3, y - 3, x2 + 3, y + 3], fill=color)
        return row

    for start_h, end_h, status in sorted_segs:
        if start_h > last_end + 0.01:
            # vertical connector + off duty gap
            new_row = draw_line_seg(last_end, start_h, "off_duty")
            if new_row != last_row:
                x = _hour_x(last_end)
                draw.line(
                    [(x, _status_y(last_row)), (x, _status_y(new_row))],
                    fill="#475569",
                    width=2,
                )
            last_row = new_row
        # connector into this segment
        row = status_map.get(status, 0)
        if row != last_row:
            x = _hour_x(start_h)
            draw.line(
                [(x, _status_y(last_row)), (x, _status_y(row))],
                fill=colors.get(status, "#334155"),
                width=2,
            )
        last_row = draw_line_seg(start_h, end_h, status)
        last_end = end_h

    if last_end < 24:
        row = draw_line_seg(last_end, 24, "off_duty")
        if row != last_row:
            x = _hour_x(last_end)
            draw.line(
                [(x, _status_y(last_row)), (x, _status_y(row))],
                fill="#475569",
                width=2,
            )

    # Remarks section
    remarks_top = graph_bottom + 55
    draw.text((40, remarks_top), "Remarks", fill="#0f172a", font=label_font)
    draw.rectangle(
        [40, remarks_top + 24, WIDTH - 40, HEIGHT - 50],
        outline="#94a3b8",
        width=1,
        fill="white",
    )
    ry = remarks_top + 34
    if not remarks:
        draw.text((50, ry), "No special remarks.", fill="#94a3b8", font=small_font)
    else:
        for line in remarks:
            draw.text((50, ry), line, fill="#334155", font=small_font)
            ry += 18

    draw.text(
        (WIDTH - 360, HEIGHT - 42),
        "Generated by Trip Planner & ELD Log Generator",
        fill="#94a3b8",
        font=tiny_font,
    )

    return img


def generate_log_images(schedule: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Generate one PNG per day from the schedule."""
    media_logs = Path(settings.MEDIA_ROOT) / "logs"
    media_logs.mkdir(parents=True, exist_ok=True)

    by_day = _parse_events_by_day(schedule)
    results: list[dict[str, str]] = []
    trip_id = uuid.uuid4().hex[:10]

    # Also attribute overnight rest segments that spill into next calendar day
    all_events = list(schedule)

    for day in sorted(by_day.keys()):
        events = by_day[day]
        day_date = events[0]["date"]
        day_start = datetime.strptime(day_date, "%Y-%m-%d")

        # Include events from adjacent days that overlap this calendar day
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
        img = draw_log_sheet(day, day_date, segments, totals, remarks)

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
