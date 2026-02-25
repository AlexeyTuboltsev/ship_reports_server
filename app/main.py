from __future__ import annotations

import asyncio
import logging
import re
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.admin_html import render_admin_page, render_fetch_history_page, render_info_page, render_request_log_page
from app import fetch_history, request_log, settings_store, stats
from app.config import (
    ADMIN_PASSWORD,
    ADMIN_USER,
    APP_VERSION,
    FETCH_HISTORY_FILE,
    PURGE_INTERVAL_SECONDS,
    REQUEST_LOG_FILE,
    SERVER_PORT,
    SETTINGS_FILE,
)
try:
    from app.info_html import INFO_HTML
except ImportError:
    INFO_HTML = "<p>Info page not generated. Run: <code>python tools/gen_info_html.py INFO.md app/info_html.py</code></p>"

from app.fetchers.ndbc import NDBCMetadata, fetch_ndbc_latest, fetch_ndbc_metadata
from app.fetchers.osmc import fetch_osmc
from app.store import StationStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

store = StationStore()
_start_time: float = 0.0
_http_client: httpx.AsyncClient | None = None  # set during lifespan

# Source status tracking
_source_status: dict[str, dict] = {
    "osmc": {"last_fetch": None, "stations": 0, "status": "pending"},
    "ndbc": {"last_fetch": None, "stations": 0, "status": "pending"},
}
_osmc_since: datetime | None = None  # None = full lookback on first fetch
_ndbc_meta = NDBCMetadata()

# Admin auth
_http_basic = HTTPBasic(auto_error=True)


def _require_admin(credentials: HTTPBasicCredentials = Depends(_http_basic)):
    if not ADMIN_USER or not ADMIN_PASSWORD:
        raise HTTPException(status_code=503, detail="Admin not configured: set ADMIN_USER and ADMIN_PASSWORD")
    ok = secrets.compare_digest(credentials.username.encode(), ADMIN_USER.encode()) and \
         secrets.compare_digest(credentials.password.encode(), ADMIN_PASSWORD.encode())
    if not ok:
        raise HTTPException(
            status_code=401,
            headers={"WWW-Authenticate": "Basic"},
        )


def _parse_age(age_str: str) -> float:
    """Parse an age string like '6h' or '30m' into hours."""
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(h|m)$", age_str.strip().lower())
    if not m:
        return 6.0  # default
    val = float(m.group(1))
    unit = m.group(2)
    if unit == "m":
        return val / 60.0
    return val


async def _fetch_osmc_task(client: httpx.AsyncClient) -> None:
    """Fetch OSMC data and update the store."""
    global _osmc_since
    try:
        fetch_start = datetime.now(timezone.utc)
        stations = await fetch_osmc(client, since=_osmc_since)
        store.update_from_osmc(stations)
        # Next fetch: only ask for data after this fetch started (minus 5 min overlap
        # to catch any observations that arrive slightly late at the OSMC endpoint).
        _osmc_since = fetch_start - timedelta(minutes=5)
        ts = fetch_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        _source_status["osmc"] = {"last_fetch": ts, "stations": len(stations), "status": "ok"}
        fetch_history.record(FETCH_HISTORY_FILE, fetch_history.FetchEvent(
            time=ts, source="osmc", status="ok", stations=len(stations), error="",
        ))
    except Exception as exc:
        logger.exception("OSMC fetch failed")
        _source_status["osmc"]["status"] = "error"
        fetch_history.record(FETCH_HISTORY_FILE, fetch_history.FetchEvent(
            time=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            source="osmc", status="error", stations=0, error=str(exc),
        ))


async def _fetch_ndbc_task(client: httpx.AsyncClient) -> None:
    """Fetch NDBC data and update the store."""
    try:
        fetch_start = datetime.now(timezone.utc)
        stations = await fetch_ndbc_latest(client, _ndbc_meta)
        store.update_from_ndbc(stations)
        ts = fetch_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        _source_status["ndbc"] = {"last_fetch": ts, "stations": len(stations), "status": "ok"}
        fetch_history.record(FETCH_HISTORY_FILE, fetch_history.FetchEvent(
            time=ts, source="ndbc", status="ok", stations=len(stations), error="",
        ))
    except Exception as exc:
        logger.exception("NDBC fetch failed")
        _source_status["ndbc"]["status"] = "error"
        fetch_history.record(FETCH_HISTORY_FILE, fetch_history.FetchEvent(
            time=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            source="ndbc", status="error", stations=0, error=str(exc),
        ))


async def _scheduler(client: httpx.AsyncClient) -> None:
    """Run periodic fetch tasks, reading intervals live from settings_store."""
    osmc_next = 0.0
    ndbc_next = 0.0
    purge_next = 0.0

    while True:
        now = time.monotonic()

        tasks = []
        if now >= osmc_next:
            tasks.append(_fetch_osmc_task(client))
            osmc_next = now + settings_store.settings.osmc_fetch_interval
        if now >= ndbc_next:
            tasks.append(_fetch_ndbc_task(client))
            ndbc_next = now + settings_store.settings.ndbc_fetch_interval
        if now >= purge_next:
            store.purge_old(settings_store.settings.max_obs_age_hours)
            purge_next = now + PURGE_INTERVAL_SECONDS

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Sleep until the next event
        next_event = min(osmc_next, ndbc_next, purge_next)
        sleep_for = max(1.0, next_event - time.monotonic())
        await asyncio.sleep(sleep_for)


async def _lookup_country(ip: str) -> None:
    """Fire-and-forget GeoIP lookup via ip-api.com. Updates stats on completion."""
    if _http_client is None:
        stats.update_country(ip, "Unknown")
        return
    try:
        resp = await _http_client.get(
            f"http://ip-api.com/json/{ip}?fields=status,countryCode",
            timeout=5.0,
        )
        data = resp.json()
        country = data.get("countryCode", "Unknown") if data.get("status") == "success" else "Unknown"
    except Exception:
        country = "Unknown"
    stats.update_country(ip, country)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _start_time, _ndbc_meta, _http_client

    _start_time = time.monotonic()

    # Load persisted settings before scheduler starts
    settings_store.load(SETTINGS_FILE)

    # Seed in-memory stats from the request log so counts survive restarts
    _total, _by_country = request_log.load_totals(REQUEST_LOG_FILE)
    stats.load_from_log(_total, _by_country)

    async with httpx.AsyncClient() as client:
        _http_client = client

        # Load NDBC metadata at startup
        try:
            _ndbc_meta = await fetch_ndbc_metadata(client)
        except Exception:
            logger.exception("Failed to load NDBC metadata at startup")

        # Start the background scheduler
        task = asyncio.create_task(_scheduler(client))
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        _http_client = None


app = FastAPI(title="Ship & Buoy Observation Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/v1/observations")
async def get_observations(
    request: Request,
    lat_min: float = Query(-90, ge=-90, le=90),
    lat_max: float = Query(90, ge=-90, le=90),
    lon_min: float = Query(-180, ge=-180, le=180),
    lon_max: float = Query(180, ge=-180, le=180),
    max_age: str = Query("6h"),
    types: str = Query("all"),
):
    t0 = time.monotonic()

    # Track request stats; fire off GeoIP lookup for new IPs
    # CF-Connecting-IP is the real client IP when behind Cloudflare
    cf_ip = request.headers.get("cf-connecting-ip", "").strip()
    xff = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    client_ip = cf_ip or xff or (request.client.host if request.client else "unknown")
    if stats.record_hit(client_ip):
        asyncio.create_task(_lookup_country(client_ip))

    age_hours = _parse_age(max_age)

    type_filter: set[str] | None = None
    if types != "all":
        type_filter = {t.strip() for t in types.split(",") if t.strip()}

    bbox = f"{lat_min:.1f},{lat_max:.1f},{lon_min:.1f},{lon_max:.1f}"
    req_time = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        results = store.query(
            lat_min=lat_min,
            lat_max=lat_max,
            lon_min=lon_min,
            lon_max=lon_max,
            max_age_hours=age_hours,
            types=type_filter,
        )
        duration_ms = int((time.monotonic() - t0) * 1000)
        request_log.record(REQUEST_LOG_FILE, request_log.RequestEvent(
            time=req_time,
            country=stats.get_country(client_ip),
            bbox=bbox,
            max_age=max_age,
            types=types,
            count=len(results),
            duration_ms=duration_ms,
            status=200,
            error="",
        ))
        return JSONResponse(
            content={
                "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "count": len(results),
                "stations": [s.to_api_dict() for s in results],
            }
        )
    except Exception as exc:
        duration_ms = int((time.monotonic() - t0) * 1000)
        request_log.record(REQUEST_LOG_FILE, request_log.RequestEvent(
            time=req_time,
            country=stats.get_country(client_ip),
            bbox=bbox,
            max_age=max_age,
            types=types,
            count=0,
            duration_ms=duration_ms,
            status=500,
            error=str(exc),
        ))
        raise


@app.api_route("/api/v1/status", methods=["GET", "HEAD"])
async def get_status():
    elapsed = time.monotonic() - _start_time
    days = int(elapsed // 86400)
    hours = int((elapsed % 86400) // 3600)
    if days > 0:
        uptime_str = f"{days}d {hours}h"
    else:
        minutes = int((elapsed % 3600) // 60)
        uptime_str = f"{hours}h {minutes}m"

    oldest = store.oldest_observation()

    return JSONResponse(
        content={
            "uptime": uptime_str,
            "sources": _source_status,
            "total_stations": store.count,
            "oldest_observation": oldest.strftime("%Y-%m-%dT%H:%M:%SZ") if oldest else None,
        }
    )


def _uptime_str() -> str:
    elapsed = time.monotonic() - _start_time
    days = int(elapsed // 86400)
    hours = int((elapsed % 86400) // 3600)
    if days > 0:
        return f"{days}d {hours}h"
    minutes = int((elapsed % 3600) // 60)
    return f"{hours}h {minutes}m"


@app.get("/admin", response_class=HTMLResponse, dependencies=[Depends(_require_admin)])
async def admin_page(msg: str = ""):
    s = stats.get_stats()
    oldest = store.oldest_observation()
    html = render_admin_page(
        generated=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        uptime=_uptime_str(),
        total_stations=store.count,
        oldest=oldest.strftime("%Y-%m-%dT%H:%M:%SZ") if oldest else None,
        sources=_source_status,
        total_requests=s["total_requests"],
        by_country=s["by_country"],
        port=SERVER_PORT,
        settings=settings_store.settings,
        version=APP_VERSION,
        flash=msg,
    )
    return HTMLResponse(content=html)


@app.get("/admin/fetch-history", response_class=HTMLResponse, dependencies=[Depends(_require_admin)])
async def fetch_history_page(
    page: int = Query(1, ge=1),
    source: str = Query(""),
    status: str = Query(""),
):
    events, total = fetch_history.load_page(
        FETCH_HISTORY_FILE, page=page, source=source, status=status,
    )
    html = render_fetch_history_page(
        events=events,
        total=total,
        page=page,
        page_size=fetch_history.PAGE_SIZE,
        source=source,
        status=status,
        version=APP_VERSION,
    )
    return HTMLResponse(content=html)


@app.get("/admin/request-log", response_class=HTMLResponse, dependencies=[Depends(_require_admin)])
async def request_log_page(
    page: int = Query(1, ge=1),
    status: str = Query(""),
):
    events, total = request_log.load_page(REQUEST_LOG_FILE, page=page, status=status)
    html = render_request_log_page(
        events=events,
        total=total,
        page=page,
        page_size=request_log.PAGE_SIZE,
        status=status,
        version=APP_VERSION,
    )
    return HTMLResponse(content=html)


@app.get("/info", response_class=HTMLResponse, dependencies=[Depends(_require_admin)])
async def info_page():
    return HTMLResponse(content=render_info_page(INFO_HTML, version=APP_VERSION))


@app.post("/admin/settings", dependencies=[Depends(_require_admin)])
async def admin_save_settings(
    osmc_fetch_interval: int = Form(...),
    ndbc_fetch_interval: int = Form(...),
    max_obs_age_hours: int = Form(...),
):
    settings_store.settings.osmc_fetch_interval = max(60, min(86400, osmc_fetch_interval))
    settings_store.settings.ndbc_fetch_interval = max(60, min(86400, ndbc_fetch_interval))
    settings_store.settings.max_obs_age_hours   = max(1,  min(168,   max_obs_age_hours))
    settings_store.save(SETTINGS_FILE)
    return RedirectResponse("/admin?msg=Settings+saved", status_code=303)


@app.post("/admin/fetch/osmc", dependencies=[Depends(_require_admin)])
async def admin_fetch_osmc():
    if _http_client is None:
        return RedirectResponse("/admin?msg=Server+not+ready", status_code=303)
    await _fetch_osmc_task(_http_client)
    return RedirectResponse("/admin?msg=OSMC+fetch+complete", status_code=303)


@app.post("/admin/fetch/ndbc", dependencies=[Depends(_require_admin)])
async def admin_fetch_ndbc():
    if _http_client is None:
        return RedirectResponse("/admin?msg=Server+not+ready", status_code=303)
    await _fetch_ndbc_task(_http_client)
    return RedirectResponse("/admin?msg=NDBC+fetch+complete", status_code=303)


@app.post("/admin/purge", dependencies=[Depends(_require_admin)])
async def admin_purge():
    n = store.purge_old(settings_store.settings.max_obs_age_hours)
    return RedirectResponse(f"/admin?msg=Purged+{n}+stale+observations", status_code=303)
