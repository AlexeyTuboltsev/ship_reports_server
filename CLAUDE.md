# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Tool Usage Rules — Always Follow

### Code Analysis
- ALWAYS use LSP tools for code analysis, diagnostics, type checking, and symbol resolution.
- Never guess at types, definitions, or errors when LSP tools are available. Use them first.

### Web Search
- ALWAYS use Firecrawl for any web search, URL fetching, or documentation lookup.
- Do not use generic Bash curl/wget for web content retrieval if Firecrawl is available.

### Git Operations
- ALWAYS use git-mcp for any git operations: commits, diffs, logs, branches, status, etc.
- Do not fall back to raw `git` Bash commands unless git-mcp explicitly fails.

## Environment & Installation Rules

### Never install directly on the host system
- If ANY task requires installing packages, runtimes, compilers, dependencies, or system tools,
  ALWAYS assume the work should happen inside a container (Docker or similar).
- Do NOT run `apt install`, `brew install`, `npm install -g`, `pip install` (system-wide),
  or any other system-level installation directly on the host machine.
- Instead: automatically propose a Dockerfile or docker-compose.yml that covers the requirement,
  and wait for approval before proceeding.
- This applies even if the install command looks harmless or temporary.
- When in doubt, ask "should this go in a container?" — the default answer is YES.

### Detect and respect existing container setup
- At the start of any task, check if a Dockerfile, docker-compose.yml, or .dockerignore
  exists in the repo root or any parent directory.
- If found AND the task involves running, building, installing, or testing anything:
  STOP and ask before proceeding.
- Do not assume the answer is yes automatically — always ask explicitly, every time.
- Only proceed after receiving a clear answer.
- If the answer is yes: all commands, builds, installs, and test runs must happen
  inside that container, not on the host.

These are standing instructions. Do not wait to be reminded. Apply them every session.

## Project Overview

**shipobs-server** — Python/FastAPI server that aggregates ship and buoy observation data
from OSMC ERDDAP and NDBC, deduplicates, and serves a compact JSON API.
Designed for self-hosting on a shore server.

The companion OpenCPN plugin (**Ship Reports**) lives in a separate repo (`ship_reports`).
It consumes this server's API to render observations as chart overlays.

API contract: `GET /api/v1/observations?lat_min=..&lat_max=..&lon_min=..&lon_max=..&max_age=6h&types=ship,buoy`
Response: compact JSON with station array (~2–10 KB per viewport).

## Structure

```
app/
├── main.py             # FastAPI app, endpoints, scheduled fetching
├── models.py           # ObservationStation dataclass
├── store.py            # In-memory station store with bbox query
├── fetchers/
│   ├── osmc.py         # OSMC ERDDAP CSV fetcher (every 15 min)
│   └── ndbc.py         # NDBC latest_obs + activestations (every 5 min)
├── dedup.py            # Merge logic, platform type normalization
└── config.py           # Settings (env-var overrides with defaults)
tests/
Dockerfile              # Production image (python:3.12-slim, non-root)
docker-compose.yml      # One-command self-hosting
pyproject.toml
```

## Commands

```bash
# Run with Docker (preferred)
docker compose up -d
docker compose logs -f

# Run locally (dev)
pip install -e .
uvicorn app.main:app --host 0.0.0.0 --port 8080

# Tests
pytest tests/ -v
```

## Docker

`Dockerfile` and `docker-compose.yml` are at the repo root. Build context is `.`.

```bash
docker compose build
docker compose up -d
curl http://localhost:8080/api/v1/status
docker compose down
```

The healthcheck polls `/api/v1/status` every 30 s with a 60 s start period
(server loads NDBC metadata at startup before first fetch).

## Configuration — Environment Variables

All have sensible defaults; override via `.env` file or inline:

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8080` | Listening port |
| `OSMC_FETCH_INTERVAL` | `900` | Seconds between OSMC fetches |
| `NDBC_FETCH_INTERVAL` | `300` | Seconds between NDBC fetches |
| `MAX_OBS_AGE_HOURS` | `12` | Discard observations older than this |

## Data Sources

- **OSMC ERDDAP** (`osmc.noaa.gov/erddap/tabledap/OSMC_flattened.csv`) — global GTS obs,
  ~4500 stations, 15-min refresh
- **NDBC latest_obs** (`ndbc.noaa.gov/data/latest_obs/latest_obs.txt`) — US buoys,
  ~800 stations, 5-min refresh
- **NDBC activestations.xml** — station metadata, fetched at startup (no local file needed)

Dedup: same `platform_code` → keep newest observation.
Platform types normalized to: `ship`, `buoy`, `drifter`, `shore`, `other`.
