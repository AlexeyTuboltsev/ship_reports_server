# Ship Reports Server — Self-Hosting

Aggregates ship and buoy observations from OSMC ERDDAP and NDBC, deduplicates
them, and serves a compact JSON API for the Ship Reports OpenCPN plugin.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 24+
- [Docker Compose](https://docs.docker.com/compose/) v2 (bundled with Docker Desktop, or `docker compose` plugin)

## Quick Start

```bash
cd server
docker compose up -d
```

The server starts on port 8080. On first startup it loads NDBC station metadata
(~60 s), then begins fetching observations in the background.

## Check Status

```bash
curl http://localhost:8080/api/v1/status
```

Example response:
```json
{"status": "ok", "station_count": 4821, "uptime_seconds": 120}
```

Query observations for a bounding box:
```bash
curl "http://localhost:8080/api/v1/observations?lat_min=50&lat_max=60&lon_min=-10&lon_max=10&max_age=6h"
```

## Configuration

All settings can be overridden via environment variables. Either pass them
inline or create a `.env` file in the `server/` directory:

```env
PORT=8080
OSMC_FETCH_INTERVAL=900   # seconds between OSMC fetches (default: 900 = 15 min)
NDBC_FETCH_INTERVAL=300   # seconds between NDBC fetches (default: 300 = 5 min)
MAX_OBS_AGE_HOURS=12      # discard observations older than this (default: 12)
```

Docker Compose automatically reads `.env` from the same directory.

To use a non-default port:
```bash
PORT=9090 docker compose up -d
```

## Update

```bash
docker compose pull
docker compose up -d
```

If you built from source (no registry), rebuild instead:
```bash
docker compose build --pull
docker compose up -d
```

## Stop / Remove

```bash
docker compose down        # stop and remove containers
docker compose down --rmi local  # also remove the built image
```

## Pointing the OpenCPN Plugin at This Server

In the Ship Reports plugin settings, set the server URL to:
```
http://<your-server-ip>:8080
```

Replace `<your-server-ip>` with the LAN or public IP of the machine running
this server.
