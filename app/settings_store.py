from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class Settings:
    osmc_fetch_interval: int = 900   # seconds
    ndbc_fetch_interval: int = 300   # seconds
    max_obs_age_hours: int = 12      # hours


# Live module-level instance — mutated by admin UI, read by scheduler
settings = Settings()


def load(path: str) -> None:
    """Populate settings from JSON file. Missing keys keep dataclass defaults."""
    p = Path(path)
    if not p.exists():
        logger.info("No settings file at %s — using defaults", path)
        return
    try:
        data = json.loads(p.read_text())
        settings.osmc_fetch_interval = int(data.get("osmc_fetch_interval", settings.osmc_fetch_interval))
        settings.ndbc_fetch_interval = int(data.get("ndbc_fetch_interval", settings.ndbc_fetch_interval))
        settings.max_obs_age_hours   = int(data.get("max_obs_age_hours",   settings.max_obs_age_hours))
        logger.info("Loaded settings from %s", path)
    except Exception:
        logger.exception("Failed to load settings from %s — using defaults", path)


def save(path: str) -> None:
    """Write current settings to JSON file."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(settings), indent=2))
    logger.info("Saved settings to %s", path)
