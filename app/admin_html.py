from __future__ import annotations


def _sources_html(sources: dict) -> str:
    rows = []
    for name, info in sources.items():
        status = info.get("status", "pending")
        cls = {"ok": "ok", "error": "err", "pending": "pend"}.get(status, "pend")
        last = info.get("last_fetch") or "\u2014"
        last_short = (last[11:19] + " UTC") if last != "\u2014" else "\u2014"
        n = info.get("stations", 0)
        rows.append(
            f'<tr><td class="lbl">{name.upper()}</td>'
            f'<td class="{cls}">{status}</td>'
            f'<td class="num">{n} stations</td>'
            f'<td class="ts">{last_short}</td></tr>'
        )
    return f'<table class="info">{"" .join(rows)}</table>'


def _country_html(by_country: dict, total: int) -> str:
    if not by_country:
        return ''
    max_count = max(by_country.values(), default=1)
    rows = []
    for country, count in sorted(by_country.items(), key=lambda x: -x[1])[:15]:
        bar_w = max(2, int(count / max_count * 100))
        pct = f"{count / total * 100:.1f}%" if total else "\u2014"
        rows.append(
            f'<tr>'
            f'<td class="lbl">{country}</td>'
            f'<td><div class="bar" style="width:{bar_w}px"></div></td>'
            f'<td class="num">{count}</td>'
            f'<td class="pct">{pct}</td>'
            f'</tr>'
        )
    return f'<table class="info">{"" .join(rows)}</table>'


_OSMC_HINT = (
    "OSMC collects global GTS observations from ships, buoys, and coastal stations. "
    "GTS has an inherent reporting delay of 1\u20132 hours, so fetching more often "
    "than every 15 min gives no benefit. Default: 900 s (15 min)."
)
_NDBC_HINT = (
    "NDBC publishes US buoy and coastal station data with only a few minutes of delay "
    "\u2014 near real-time. Default: 300 s (5 min)."
)
_MAX_AGE_HINT = "Observations older than this are discarded from the in-memory store. Default: 12 h."


def _settings_html(port: int, osmc_interval: int, ndbc_interval: int, max_age: int) -> str:
    return (
        f'<table class="info" style="margin-bottom:.7rem">'
        f'<tr><td class="lbl">API port</td>'
        f'<td class="value">{port}'
        f'<div class="hint">Port the observation API listens on. Set in .env and docker-compose.yml.</div>'
        f'</td></tr>'
        f'</table>'
        f'<form method="post" action="/admin/settings">'
        f'<table class="info" style="margin-bottom:.6rem">'
        f'<tr><td class="lbl">OSMC fetch interval</td>'
        f'<td><input class="si" type="number" name="osmc_fetch_interval" value="{osmc_interval}" min="60" max="86400"> s'
        f'<div class="hint">{_OSMC_HINT}</div></td></tr>'
        f'<tr><td class="lbl">NDBC fetch interval</td>'
        f'<td><input class="si" type="number" name="ndbc_fetch_interval" value="{ndbc_interval}" min="60" max="86400"> s'
        f'<div class="hint">{_NDBC_HINT}</div></td></tr>'
        f'<tr><td class="lbl">Max obs age</td>'
        f'<td><input class="si" type="number" name="max_obs_age_hours" value="{max_age}" min="1" max="168"> h'
        f'<div class="hint">{_MAX_AGE_HINT}</div></td></tr>'
        f'</table>'
        f'<button type="submit">&#10003; Save settings</button>'
        f'</form>'
    )


_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>shipobs admin</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#f6f8fa;color:#24292f;font:13px/1.6 "Courier New",monospace;padding:1.5rem}}
h1{{color:#0969da;font-size:1.1rem;margin-bottom:1rem;letter-spacing:.05em}}
h2{{color:#0969da;font-size:.78rem;text-transform:uppercase;letter-spacing:.12em;
    margin-bottom:.6rem;padding-bottom:.4rem;border-bottom:1px solid #d0d7de}}
.topbar{{display:flex;justify-content:space-between;align-items:center;
         margin-bottom:1.2rem;font-size:.78rem;color:#656d76}}
.topbar select{{background:#fff;color:#24292f;border:1px solid #d0d7de;
                padding:.15rem .3rem;font-size:.78rem;border-radius:3px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem}}
.card{{background:#fff;border:1px solid #d0d7de;border-radius:6px;padding:1rem}}
table.info{{width:100%;border-collapse:collapse}}
table.info td{{padding:.15rem .3rem;vertical-align:middle}}
.lbl{{color:#656d76;min-width:5rem}}
.num{{text-align:right;min-width:3.5rem}}
.pct{{text-align:right;color:#656d76;min-width:3rem}}
.ts{{color:#656d76;font-size:.75rem;text-align:right}}
.ok{{color:#1a7f37}}.err{{color:#d1242f}}.pend{{color:#9a6700}}
.bar{{background:#0969da;height:.55em;border-radius:2px;display:inline-block;min-width:2px}}
.big{{font-size:1.4rem;color:#24292f;font-weight:bold}}
.actions form{{margin:.3rem 0}}
.actions button{{
  background:#fff;color:#0969da;border:1px solid #d0d7de;
  padding:.35rem .8rem;cursor:pointer;font:13px "Courier New",monospace;
  border-radius:4px;width:100%;text-align:left;transition:background .15s}}
.actions button:hover{{background:#0969da;color:#fff;border-color:#0969da}}
.actions button.danger{{color:#d1242f;border-color:#d0d7de}}
.actions button.danger:hover{{background:#d1242f;color:#fff;border-color:#d1242f}}
.flash{{background:#dafbe1;border:1px solid #1a7f37;color:#1a7f37;
        padding:.4rem .8rem;margin-bottom:1rem;border-radius:4px;font-size:.82rem}}
.flash.warn{{background:#fff8c5;border-color:#9a6700;color:#9a6700}}
.si{{background:#f6f8fa;color:#24292f;border:1px solid #d0d7de;padding:.15rem .3rem;
     width:5rem;font:13px "Courier New",monospace;border-radius:3px}}
.hint{{color:#656d76;font-size:.72rem;margin-top:.2rem;line-height:1.4}}
@media(max-width:600px){{.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<h1>&#9881; shipobs-server / admin &nbsp;<a href="/info" style="font-size:.75rem;color:#656d76;text-decoration:none;font-weight:normal">info &amp; sources &#8599;</a> &nbsp;<a href="/admin/fetch-history" style="font-size:.75rem;color:#656d76;text-decoration:none;font-weight:normal">fetch history &#8599;</a></h1>
{flash}
<div class="topbar">
  <span>v{version}</span>
  <span>auto-refresh:&nbsp;<select id="rsel" onchange="setR(this.value)">
    <option value="0">off</option>
    <option value="5">5 s</option>
    <option value="10">10 s</option>
    <option value="30">30 s</option>
    <option value="60">60 s</option>
  </select>&nbsp;&nbsp;updated: {generated}</span>
</div>

<div class="grid">
  <div class="card">
    <h2>Server</h2>
    <table class="info">
      <tr><td class="lbl">uptime</td><td class="value">{uptime}</td></tr>
      <tr><td class="lbl">stations (deduplicated)</td><td><span class="big">{total_stations}</span></td></tr>
      <tr><td class="lbl">oldest observation</td><td class="ts" style="text-align:left">{oldest}</td></tr>
    </table>
  </div>
  <div class="card">
    <h2>Sources \u2014 latest fetch</h2>
    {sources_html}
  </div>
</div>

<div class="grid">
  <div class="card">
    <h2>API Requests</h2>
    <table class="info" style="margin-bottom:.6rem">
      <tr><td class="lbl">total</td><td><span class="big">{total_requests}</span></td></tr>
    </table>
    {country_html}
  </div>
  <div class="card">
    <h2>Settings</h2>
    {settings_html}
  </div>
</div>

<div class="grid">
  <div class="card actions">
    <h2>Actions</h2>
    <form method="post" action="/admin/fetch/osmc">
      <button type="submit">&#8635; Trigger OSMC fetch</button>
    </form>
    <form method="post" action="/admin/fetch/ndbc">
      <button type="submit">&#8635; Trigger NDBC fetch</button>
    </form>
    <form method="post" action="/admin/purge"
          onsubmit="return confirm('Purge all observations older than MAX_OBS_AGE_HOURS?')">
      <button type="submit" class="danger">&#10005; Purge stale observations</button>
    </form>
  </div>
</div>


<script>
var _rt=null;
function setR(v){{
  localStorage.setItem('ar',v);
  if(_rt)clearTimeout(_rt);
  if(parseInt(v)>0)_rt=setTimeout(function(){{location.reload();}},v*1000);
}}
(function(){{
  var v=localStorage.getItem('ar')||'10';
  document.getElementById('rsel').value=v;
  setR(v);
}})();
</script>
</body>
</html>
"""


def render_admin_page(
    *,
    generated: str,
    uptime: str,
    total_stations: int,
    oldest: str | None,
    sources: dict,
    total_requests: int,
    by_country: dict,
    port: int,
    settings,
    version: str = "",
    flash: str = "",
    flash_warn: bool = False,
) -> str:
    flash_html = ""
    if flash:
        cls = "flash warn" if flash_warn else "flash"
        flash_html = f'<div class="{cls}">{flash}</div>'

    return _PAGE.format(
        flash=flash_html,
        generated=generated,
        uptime=uptime,
        total_stations=total_stations,
        oldest=oldest or "\u2014",
        sources_html=_sources_html(sources),
        total_requests=total_requests,
        country_html=_country_html(by_country, total_requests),
        settings_html=_settings_html(
            port,
            settings.osmc_fetch_interval,
            settings.ndbc_fetch_interval,
            settings.max_obs_age_hours,
        ),
        version=version,
    )


_INFO_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>shipobs \u2014 info</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#f6f8fa;color:#24292f;font:14px/1.7 Georgia,serif;padding:1.5rem}}
nav{{margin-bottom:1.5rem;font-size:.8rem;font-family:"Courier New",monospace}}
nav a{{color:#0969da;text-decoration:none}}
nav a:hover{{text-decoration:underline}}
.content{{max-width:780px}}
h1{{color:#0969da;font-size:1.2rem;margin:1.2rem 0 .5rem;font-family:"Courier New",monospace}}
h2{{color:#0969da;font-size:1rem;margin:1.4rem 0 .4rem;padding-bottom:.3rem;border-bottom:1px solid #d0d7de;font-family:"Courier New",monospace}}
h3{{color:#24292f;font-size:.9rem;margin:1rem 0 .3rem;font-family:"Courier New",monospace}}
p{{margin-bottom:.8rem}}
a{{color:#0969da;text-decoration:none}}
a:hover{{text-decoration:underline}}
hr{{border:none;border-top:1px solid #d0d7de;margin:1.2rem 0}}
ul{{margin:.4rem 0 .8rem 1.4rem}}
li{{margin:.25rem 0}}
table{{border-collapse:collapse;margin:.5rem 0 .8rem;width:100%}}
td{{padding:.35rem .6rem;border:1px solid #d0d7de;vertical-align:top}}
tr:first-child td{{color:#656d76;font-size:.8rem;background:#f0f3f6}}
b{{color:#0969da}}
code{{background:#eef0f3;padding:.1rem .3rem;border-radius:3px;font-size:.85rem;font-family:"Courier New",monospace}}
pre{{background:#eef0f3;padding:.7rem 1rem;border-radius:4px;overflow-x:auto;margin:.5rem 0 .8rem}}
pre code{{background:none;padding:0}}
</style>
</head>
<body>
<nav><a href="/admin">&#8592; admin</a>&nbsp;&nbsp;v{version}</nav>
<div class="content">
{info_body}
</div>
</body>
</html>
"""


def render_info_page(info_html: str, version: str = "") -> str:
    return _INFO_PAGE.format(info_body=info_html, version=version)


_FETCH_HISTORY_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>shipobs \u2014 fetch history</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#f6f8fa;color:#24292f;font:13px/1.6 "Courier New",monospace;padding:1.5rem}}
nav{{margin-bottom:1.2rem;font-size:.8rem}}
nav a{{color:#0969da;text-decoration:none}}
nav a:hover{{text-decoration:underline}}
h1{{color:#0969da;font-size:1.1rem;margin-bottom:.6rem;letter-spacing:.05em}}
.meta{{color:#656d76;font-size:.78rem;margin-bottom:.8rem}}
table{{width:100%;border-collapse:collapse;background:#fff;border:1px solid #d0d7de;border-radius:6px;overflow:hidden}}
th{{background:#f0f3f6;color:#656d76;font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;
    padding:.4rem .6rem;border-bottom:1px solid #d0d7de;text-align:left;white-space:nowrap}}
td{{padding:.25rem .6rem;border-bottom:1px solid #f0f3f6;vertical-align:top}}
tr:last-child td{{border-bottom:none}}
.ok{{color:#1a7f37}}.err{{color:#d1242f}}
.num{{text-align:right}}
.ts{{color:#656d76;white-space:nowrap}}
.err-msg{{color:#d1242f;font-size:.75rem;word-break:break-all}}
.topbar{{display:flex;justify-content:space-between;align-items:center;margin-bottom:.8rem;font-size:.78rem;color:#656d76}}
.topbar h1{{margin-bottom:0}}
.topbar select{{background:#fff;color:#24292f;border:1px solid #d0d7de;padding:.15rem .3rem;font-size:.78rem;border-radius:3px}}
.filters{{display:flex;gap:1.5rem;margin-bottom:.8rem;font-size:.78rem;flex-wrap:wrap}}
.filters span{{color:#656d76}}
.filters a{{color:#0969da;text-decoration:none;padding:.1rem .35rem;border-radius:3px}}
.filters a:hover{{background:#e8f0fe}}
.filters a.active{{background:#0969da;color:#fff}}
.pager{{margin-top:1rem;font-size:.8rem;display:flex;gap:1.2rem;align-items:center;color:#656d76}}
.pager a{{color:#0969da;text-decoration:none}}
.pager a:hover{{text-decoration:underline}}
.pager .dim{{color:#d0d7de}}
</style>
</head>
<body>
<nav><a href="/admin">&#8592; admin</a>&nbsp;&nbsp;v{{version}}</nav>
<div class="topbar">
  <h1>Fetch History</h1>
  <span>auto-refresh:&nbsp;<select id="rsel" onchange="setR(this.value)">
    <option value="0">off</option>
    <option value="5">5 s</option>
    <option value="10">10 s</option>
    <option value="30">30 s</option>
    <option value="60">60 s</option>
  </select></span>
</div>
<p class="meta">{total} events &nbsp;&#8212;&nbsp; page {page} of {total_pages}</p>
{filters}
{table}
{pager}
<script>
var _rt=null;
function setR(v){{
  localStorage.setItem('ar',v);
  if(_rt)clearTimeout(_rt);
  if(parseInt(v)>0)_rt=setTimeout(function(){{location.reload();}},v*1000);
}}
(function(){{
  var v=localStorage.getItem('ar')||'10';
  document.getElementById('rsel').value=v;
  setR(v);
}})();
</script>
</body>
</html>
"""


def _fetch_history_table(events: list) -> str:
    if not events:
        rows = '<tr><td colspan="5" style="color:#656d76;text-align:center;padding:.8rem">no matching entries</td></tr>'
    else:
        row_parts = []
        for e in events:
            cls = "ok" if e.status == "ok" else "err"
            stn = str(e.stations) if e.status == "ok" else "\u2014"
            err = f'<span class="err-msg">{e.error}</span>' if e.error else ""
            row_parts.append(
                f'<tr>'
                f'<td class="ts">{e.time}</td>'
                f'<td>{e.source.upper()}</td>'
                f'<td class="{cls}">{e.status}</td>'
                f'<td class="num">{stn}</td>'
                f'<td>{err}</td>'
                f'</tr>'
            )
        rows = "".join(row_parts)
    return (
        '<table>'
        '<thead><tr>'
        '<th>Time (UTC)</th><th>Source</th><th>Status</th>'
        '<th style="text-align:right">Stations</th><th>Error</th>'
        '</tr></thead>'
        f'<tbody>{rows}</tbody>'
        '</table>'
    )


def _filters_html(source: str, status: str) -> str:
    def link(label: str, qs: str, active: bool) -> str:
        cls = ' class="active"' if active else ""
        return f'<a href="/admin/fetch-history?{qs}"{cls}>{label}</a>'

    def qs(s: str, st: str) -> str:
        parts = []
        if s:
            parts.append(f"source={s}")
        if st:
            parts.append(f"status={st}")
        return "&".join(parts)

    src_links = (
        f'<span>source:</span>'
        + link("all", qs("", status), source == "")
        + link("OSMC", qs("osmc", status), source == "osmc")
        + link("NDBC", qs("ndbc", status), source == "ndbc")
    )
    st_links = (
        f'<span>status:</span>'
        + link("all", qs(source, ""), status == "")
        + link("ok", qs(source, "ok"), status == "ok")
        + link("error", qs(source, "error"), status == "error")
    )
    return f'<div class="filters">{src_links}&nbsp;&nbsp;{st_links}</div>'


def _pager_html(page: int, total_pages: int, source: str = "", status: str = "") -> str:
    def url(p: int) -> str:
        parts = [f"page={p}"]
        if source:
            parts.append(f"source={source}")
        if status:
            parts.append(f"status={status}")
        return "/admin/fetch-history?" + "&".join(parts)

    prev = (f'<a href="{url(page - 1)}">&#8592; newer</a>'
            if page > 1 else '<span class="dim">&#8592; newer</span>')
    nxt = (f'<a href="{url(page + 1)}">older &#8594;</a>'
           if page < total_pages else '<span class="dim">older &#8594;</span>')
    return f'<div class="pager">{prev}<span>page {page} / {total_pages}</span>{nxt}</div>'


def render_fetch_history_page(
    *,
    events: list,
    total: int,
    page: int,
    page_size: int,
    source: str = "",
    status: str = "",
    version: str = "",
) -> str:
    import math
    total_pages = max(1, math.ceil(total / page_size))
    page = max(1, min(page, total_pages))
    # _FETCH_HISTORY_PAGE uses {{ }} for CSS braces but {version} etc for values,
    # so we format version separately via a simple replace to avoid double-format issues.
    html = _FETCH_HISTORY_PAGE.replace("{{version}}", version)
    return html.format(
        total=total,
        page=page,
        total_pages=total_pages,
        filters=_filters_html(source, status),
        table=_fetch_history_table(events),
        pager=_pager_html(page, total_pages, source, status),
    )
