# Ship Reports Server — Self-Hosting

**Source:** https://github.com/AlexeyTuboltsev/ship_reports_server

Aggregates ship and buoy observations from OSMC ERDDAP and NDBC, deduplicates
them, and serves a compact JSON API for the Ship Reports OpenCPN plugin.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 24+
- [Docker Compose](https://docs.docker.com/compose/) v2 (bundled with Docker Desktop, or `docker compose` plugin)

## Setup

**1. Clone the repository**

```bash
git clone https://github.com/AlexeyTuboltsev/ship_reports_server.git
cd ship_reports_server
```

**2. Create your `.env` file**

```bash
cp .env.example .env
```

Then edit `.env` and set a strong admin password:

```env
PORT=8080
ADMIN_USER=admin
ADMIN_PASSWORD=yourpassword
```

> `PORT` is the port the server will listen on. `ADMIN_USER` and `ADMIN_PASSWORD`
> protect the `/admin` interface — change them from the defaults before exposing
> the server to a network.

**3. Build and start**

```bash
docker compose up -d --build
```

On first startup the server loads NDBC station metadata (allow ~60 s), then
begins fetching observations in the background.

**4. Verify**

```bash
docker compose logs -f          # watch startup logs
curl http://localhost:8080/api/v1/status
```

Open `http://localhost:8080/admin` in your browser and log in with the
credentials from `.env`.

## Configuration

Fetch intervals and max observation age are managed at runtime via the admin UI
and persisted to a Docker volume (`shipobs_data:/data`). No restart needed.

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
