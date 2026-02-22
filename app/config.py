from __future__ import annotations

import os

OSMC_BASE_URL = (
    "https://osmc.noaa.gov/erddap/tabledap/OSMC_flattened.csv"
)
OSMC_FIELDS = (
    "platform_code,platform_type,country,latitude,longitude,time,"
    "sst,atmp,slp,windspd,winddir,wvht,waterlevel,clouds,dewpoint"
)
OSMC_LOOKBACK_HOURS = 6
NDBC_LATEST_OBS_URL = (
    "https://www.ndbc.noaa.gov/data/latest_obs/latest_obs.txt"
)
NDBC_ACTIVE_STATIONS_URL = (
    "https://www.ndbc.noaa.gov/activestations.xml"
)

PURGE_INTERVAL_SECONDS = 15 * 60  # 15 minutes

SETTINGS_FILE = os.getenv("SETTINGS_FILE", "/data/settings.json")

SERVER_HOST = "0.0.0.0"
SERVER_PORT = int(os.getenv("PORT", "8080"))

HTTP_TIMEOUT_SECONDS = 30

ADMIN_USER = os.getenv("ADMIN_USER", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
