# Ship Reports Plugin

Near real-time meteorological observations from ships, buoys, and coastal stations in OpenCPN

---

## About this server

This is the server side of the Ship Reports plugin. It fetches and aggregates observation data from multiple sources, deduplicates overlapping reports, and serves a compact JSON API that the plugin consumes. You are looking at its admin interface.

The plugin repository is at <https://github.com/AlexeyTuboltsev/ship_reports>.

---

## Connecting the plugin to this server

In OpenCPN, open the Ship Reports plugin settings (Plugins menu → Ship Reports → Settings) and set **Server URL** to:

```
http://<your-server-address>:<port>
```

Replace `<your-server-address>` with the IP or hostname of the machine running this server, and `<port>` with the port configured in your `.env` file (default: `8080`). For example:

```
http://192.168.1.10:8080
```

If you are running the plugin on the same machine as the server, use `http://localhost:8080`.

---

## Data sources

We collect data from multiple sources trying to get the best coverage possible.
Please get in touch if you can suggest additional data sources.

### OSMC — Ocean Surface Marine Observations
**URL:** <https://osmc.noaa.gov>
**Data endpoint:** <https://osmc.noaa.gov/erddap/tabledap/OSMC_flattened.csv>

The OSMC (Observing System Monitoring Center) collects and quality-controls real-time in-situ surface marine observations from the Global Telecommunication System (GTS). It covers ships, moored and drifting buoys, coastal tide gauges, and C-MAN stations worldwide. The server refreshes OSMC data every 15 minutes.

On first startup the server fetches the full 6-hour observation window from OSMC (typically 50 000–80 000 rows). After that, each 15-minute refresh requests only observations newer than the previous fetch, so subsequent updates are a small incremental batch rather than the full dataset.

Note: GTS observations have an inherent reporting delay of roughly 1–2 hours between measurement and availability. Displayed OSMC observations are therefore typically 1–2 hours old regardless of when the last fetch occurred.

Typical coverage: ~4 000–5 000 active stations globally.

### NDBC — National Data Buoy Center
**URL:** <https://www.ndbc.noaa.gov>
**Data endpoint:** <https://www.ndbc.noaa.gov/data/latest_obs/latest_obs.txt>
**Station metadata:** <https://www.ndbc.noaa.gov/activestations.xml>

NDBC (operated by NOAA) maintains a network of moored buoys and coastal stations along US coasts, the Great Lakes, and open ocean. Observations include wind, wave height, sea temperature, and atmospheric pressure. The server refreshes NDBC data every 5 minutes; NDBC publishes observations with only a few minutes of delay, so displayed data is near-real-time.

The NDBC endpoint (`latest_obs.txt`) is a compact snapshot file that always contains exactly one current reading per active station. Every fetch retrieves the full set (~800–900 rows, ~50 KB), so no incremental optimisation is needed or possible.

Typical coverage: ~800–900 active US buoys and coastal stations.

---

## What are ship reports

The observations displayed by this plugin come from a global network of platforms that have been collecting and sharing surface marine weather data for over a century, coordinated by the World Meteorological Organization (WMO) and national meteorological agencies.

### Voluntary Observing Ships (VOS)

Merchant vessels, ferries, research ships, and yachts can enlist with their national meteorological service to become Voluntary Observing Ships. Crew members take regular observations — wind speed and direction, air and sea temperature, pressure, visibility, wave height — and transmit them in standardised WMO format over the Global Telecommunication System (GTS). The programme is coordinated by the WMO Ship Observations Team and has been running since the 1850s. Around 3 000–4 000 VOS ships are active at any one time, providing invaluable coverage of otherwise data-sparse ocean regions.

### Moored buoys

Moored buoys are anchored to the seabed and carry automated sensor suites that measure wind, waves, sea surface temperature, salinity, and atmospheric pressure continuously. Networks are operated by national agencies — NOAA's National Data Buoy Center (NDBC) covers US waters, while the international Data Buoy Cooperation Panel (DBCP), a joint WMO/IOC body, coordinates global deployment. Moored buoys are particularly important for storm and wave monitoring and for validating satellite data.

### Drifting buoys

Drifting buoys are free-floating platforms that drift with ocean currents while measuring sea surface temperature and atmospheric pressure. NOAA's Global Drifter Program (part of the Global Ocean Observing System) maintains a target array of around 1 250 drifters spread evenly across all ocean basins. Their tracks also provide direct measurements of near-surface ocean currents.

### Coastal and shore stations

Fixed automated weather stations are installed on lighthouses, offshore oil platforms, piers, and island outposts. NOAA's Coastal-Marine Automated Network (C-MAN) and similar national networks provide high-frequency observations from coastal chokepoints and port approaches that are critical for near-shore navigation and safety.

---

## Authors

- Vibe: Alexey Tuboltsev
  [tblz@proton.me](mailto:tblz@proton.me)
  [github.com/AlexeyTuboltsev](https://github.com/AlexeyTuboltsev)

- Coding: Claude Code
  [anthropic.com](https://anthropic.com)
