# Ship Reports Server — Self-Hosting

**Source:** https://github.com/AlexeyTuboltsev/ship_reports_server

Aggregates ship and buoy observations from OSMC ERDDAP and NDBC, deduplicates
them, and serves a compact JSON API for the Ship Reports OpenCPN plugin.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 24+
- [Docker Compose](https://docs.docker.com/compose/) v2 (bundled with Docker Desktop, or `docker compose` plugin)

## Quick Start

```bash
cp .env.example .env
# Edit .env — set PORT, ADMIN_USER, ADMIN_PASSWORD
docker compose up -d --build
```

The server starts on the configured port. On first startup it loads NDBC station
metadata (~60 s), then begins fetching observations in the background.

## Configuration

Copy `.env.example` to `.env` and edit:

```env
PORT=8080
ADMIN_USER=admin
ADMIN_PASSWORD=yourpassword
```

Fetch intervals and max observation age are managed at runtime via the admin UI
and persisted to a Docker volume (`shipobs_data:/data`).

## Admin UI

Open `http://localhost:8080/admin` in your browser (replace port as needed).
Log in with the credentials from `.env`. From there you can:

- Monitor source fetch status and station counts
- Adjust OSMC/NDBC fetch intervals and max observation age
- Trigger manual fetches
- Purge stale observations
- View API request stats by country

## Check Status

```bash
curl http://localhost:8080/api/v1/status
```

Query observations for a bounding box:
```bash
curl "http://localhost:8080/api/v1/observations?lat_min=50&lat_max=60&lon_min=-10&lon_max=10&max_age=6h"
```

## Update

```bash
docker compose build --pull
docker compose up -d
```

## Stop / Remove

```bash
docker compose down              # stop and remove containers
docker compose down --rmi local  # also remove the built image
```

## Pointing the OpenCPN Plugin at This Server

In the Ship Reports plugin settings, set the server URL to:
```
http://<your-server-ip>:8080
```

Replace `<your-server-ip>` with the LAN or public IP of the machine running
this server.
