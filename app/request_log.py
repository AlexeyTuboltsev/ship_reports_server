from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

PAGE_SIZE = 15
MAX_ENTRIES = 5000


@dataclass
class RequestEvent:
    time: str        # ISO-8601 UTC
    country: str     # country code, "Local", or "" if still pending
    bbox: str        # "lat_min,lat_max,lon_min,lon_max"
    max_age: str     # e.g. "6h"
    types: str       # e.g. "all" or "ship,buoy"
    count: int       # returned observation count
    duration_ms: int
    status: int      # HTTP status code
    error: str       # "" on success


def record(path: str, event: RequestEvent) -> None:
    """Append one request event to the JSONL file. Rotates at MAX_ENTRIES."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({
        "time": event.time,
        "country": event.country,
        "bbox": event.bbox,
        "max_age": event.max_age,
        "types": event.types,
        "count": event.count,
        "duration_ms": event.duration_ms,
        "status": event.status,
        "error": event.error,
    }) + "\n"
    try:
        if p.exists():
            content = p.read_text(encoding="utf-8")
            lines = content.splitlines()
            if len(lines) >= MAX_ENTRIES:
                lines = lines[-(MAX_ENTRIES - 1):]
                p.write_text("\n".join(lines) + "\n" + line, encoding="utf-8")
                return
        with p.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        logger.exception("Failed to write request log to %s", path)


def load_page(
    path: str,
    page: int = 1,
    status: str = "",  # "ok" | "error"
) -> tuple[list[RequestEvent], int]:
    """Return (events, total_filtered) for the given page, newest first.

    Optionally filter by status: "ok" (HTTP 2xx) or "error" (HTTP 4xx/5xx).
    Page is 1-based.
    """
    p = Path(path)
    if not p.exists():
        return [], 0
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except Exception:
        logger.exception("Failed to read request log from %s", path)
        return [], 0

    valid = [l for l in lines if l.strip()]
    valid.reverse()  # newest first

    all_events: list[RequestEvent] = []
    for line in valid:
        try:
            d = json.loads(line)
            ev_status = int(d.get("status", 200))
            is_ok = ev_status < 400
            if status == "ok" and not is_ok:
                continue
            if status == "error" and is_ok:
                continue
            all_events.append(RequestEvent(
                time=d.get("time", ""),
                country=d.get("country", ""),
                bbox=d.get("bbox", ""),
                max_age=d.get("max_age", ""),
                types=d.get("types", ""),
                count=int(d.get("count", 0)),
                duration_ms=int(d.get("duration_ms", 0)),
                status=ev_status,
                error=d.get("error", ""),
            ))
        except Exception:
            pass

    total = len(all_events)
    start = (page - 1) * PAGE_SIZE
    return all_events[start: start + PAGE_SIZE], total
