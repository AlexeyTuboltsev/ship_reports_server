from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

PAGE_SIZE = 15


@dataclass
class FetchEvent:
    time: str      # ISO-8601 UTC
    source: str    # "osmc" | "ndbc"
    status: str    # "ok" | "error"
    stations: int  # 0 on error
    error: str     # "" on success


def record(path: str, event: FetchEvent) -> None:
    """Append one fetch event to the JSONL file. Creates the file/dirs if needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({
        "time": event.time,
        "source": event.source,
        "status": event.status,
        "stations": event.stations,
        "error": event.error,
    }) + "\n"
    try:
        with p.open("a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        logger.exception("Failed to write fetch history to %s", path)


def load_page(
    path: str,
    page: int = 1,
    source: str = "",
    status: str = "",
) -> tuple[list[FetchEvent], int]:
    """Return (events, total_filtered) for the given page, newest first.

    Optionally filter by source ("osmc"|"ndbc") and/or status ("ok"|"error").
    Page is 1-based.
    """
    p = Path(path)
    if not p.exists():
        return [], 0
    try:
        lines = p.read_text(encoding="utf-8").splitlines()
    except Exception:
        logger.exception("Failed to read fetch history from %s", path)
        return [], 0

    valid = [l for l in lines if l.strip()]
    valid.reverse()  # newest first

    # Parse and filter
    all_events: list[FetchEvent] = []
    for line in valid:
        try:
            d = json.loads(line)
            if source and d.get("source") != source:
                continue
            if status and d.get("status") != status:
                continue
            all_events.append(FetchEvent(
                time=d.get("time", ""),
                source=d.get("source", ""),
                status=d.get("status", ""),
                stations=int(d.get("stations", 0)),
                error=d.get("error", ""),
            ))
        except Exception:
            pass

    total = len(all_events)
    start = (page - 1) * PAGE_SIZE
    return all_events[start: start + PAGE_SIZE], total
