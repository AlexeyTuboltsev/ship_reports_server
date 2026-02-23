#!/usr/bin/env bash
# Pull latest code and redeploy. Run from the repo root.
set -euo pipefail

git pull
docker compose up -d --build
docker compose ps
