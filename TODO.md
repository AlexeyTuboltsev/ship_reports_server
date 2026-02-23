# TODO

## Admin UI
- [x] Add info block listing data sources (OSMC, NDBC) with links
- [x] Add hints/tooltips explaining OSMC and NDBC fetch frequency fields
- [x] Replace bare port number with explanation of what it means
- [ ] Add About block (version, project link)
- [ ] Fix string translations

## Documentation
- [x] README: add setup instructions
- [ ] Plugin: add server setup instructions to plugin info/help

## Features
- [x] Fetch history log (per-fetch JSONL with source, status, station count)
- [x] Request log (per-request JSONL with bbox, country, duration, status)
- [x] OSMC incremental fetch (first full lookback, subsequent fetches incremental)
- [x] Version tracking (setuptools-scm, shown in admin topbar)
- [x] GeoIP country tracking in admin UI

## Infrastructure
- [x] EC2 deployment (t4g.micro, eu-central-1)
- [x] Domain + Cloudflare HTTPS (opencpn-tools.org)
- [x] Container auto-restart (restart: unless-stopped)
- [ ] Docker log rotation (max-size: 10m, max-file: 3)
- [ ] Cloudflare real IP: verify CF-Connecting-IP works correctly for GeoIP
- [ ] External uptime monitoring (UptimeRobot → /api/v1/status)

## Tests
- [ ] Review existing test coverage
- [ ] Tests for fetch_history, request_log, admin endpoints
