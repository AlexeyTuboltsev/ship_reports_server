from __future__ import annotations


def _sources_html(sources: dict) -> str:
    rows = []
    for name, info in sources.items():
        status = info.get("status", "pending")
        cls = {"ok": "ok", "error": "err", "pending": "pend"}.get(status, "pend")
        last = info.get("last_fetch") or "—"
        last_short = last[11:19] if last != "—" else "—"
        n = info.get("stations", 0)
        rows.append(
            f'<tr><td class="lbl">{name.upper()}</td>'
            f'<td class="{cls}">{status}</td>'
            f'<td class="num">{n} stn</td>'
            f'<td class="ts">{last_short}</td></tr>'
        )
    return f'<table class="info">{"".join(rows)}</table>'


def _country_html(by_country: dict, total: int) -> str:
    if not by_country:
        return '<span class="lbl">no data yet</span>'
    max_count = max(by_country.values(), default=1)
    rows = []
    for country, count in sorted(by_country.items(), key=lambda x: -x[1])[:15]:
        bar_w = max(2, int(count / max_count * 100))
        pct = f"{count / total * 100:.1f}%" if total else "—"
        rows.append(
            f'<tr>'
            f'<td class="lbl">{country}</td>'
            f'<td><div class="bar" style="width:{bar_w}px"></div></td>'
            f'<td class="num">{count}</td>'
            f'<td class="pct">{pct}</td>'
            f'</tr>'
        )
    return f'<table class="info">{"".join(rows)}</table>'


def _settings_html(port: int, osmc_interval: int, ndbc_interval: int, max_age: int) -> str:
    return (
        f'<table class="info" style="margin-bottom:.7rem">'
        f'<tr><td class="lbl">API port</td><td class="value">{port}</td></tr>'
        f'</table>'
        f'<form method="post" action="/admin/settings">'
        f'<table class="info" style="margin-bottom:.6rem">'
        f'<tr><td class="lbl">OSMC interval</td>'
        f'<td><input class="si" type="number" name="osmc_fetch_interval" value="{osmc_interval}" min="60" max="86400"> s</td></tr>'
        f'<tr><td class="lbl">NDBC interval</td>'
        f'<td><input class="si" type="number" name="ndbc_fetch_interval" value="{ndbc_interval}" min="60" max="86400"> s</td></tr>'
        f'<tr><td class="lbl">Max obs age</td>'
        f'<td><input class="si" type="number" name="max_obs_age_hours" value="{max_age}" min="1" max="168"> h</td></tr>'
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
body{{background:#0d1117;color:#c9d1d9;font:13px/1.6 "Courier New",monospace;padding:1.5rem}}
h1{{color:#58a6ff;font-size:1.1rem;margin-bottom:1rem;letter-spacing:.05em}}
h2{{color:#58a6ff;font-size:.78rem;text-transform:uppercase;letter-spacing:.12em;
    margin-bottom:.6rem;padding-bottom:.4rem;border-bottom:1px solid #21262d}}
.topbar{{display:flex;justify-content:space-between;align-items:center;
         margin-bottom:1.2rem;font-size:.78rem;color:#8b949e}}
.topbar select{{background:#161b22;color:#c9d1d9;border:1px solid #30363d;
                padding:.15rem .3rem;font-size:.78rem;border-radius:3px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1rem}}
.card{{background:#161b22;border:1px solid #21262d;border-radius:6px;padding:1rem}}
table.info{{width:100%;border-collapse:collapse}}
table.info td{{padding:.15rem .3rem;vertical-align:middle}}
.lbl{{color:#8b949e;min-width:5rem}}
.num{{text-align:right;min-width:3.5rem}}
.pct{{text-align:right;color:#8b949e;min-width:3rem}}
.ts{{color:#8b949e;font-size:.75rem;text-align:right}}
.ok{{color:#3fb950}}.err{{color:#f85149}}.pend{{color:#d29922}}
.bar{{background:#1f6feb;height:.55em;border-radius:2px;display:inline-block;min-width:2px}}
.big{{font-size:1.4rem;color:#c9d1d9;font-weight:bold}}
.actions form{{margin:.3rem 0}}
.actions button{{
  background:#161b22;color:#58a6ff;border:1px solid #30363d;
  padding:.35rem .8rem;cursor:pointer;font:13px "Courier New",monospace;
  border-radius:4px;width:100%;text-align:left;transition:background .15s}}
.actions button:hover{{background:#1f6feb;color:#fff;border-color:#1f6feb}}
.actions button.danger{{color:#f85149;border-color:#30363d}}
.actions button.danger:hover{{background:#f85149;color:#fff;border-color:#f85149}}
.flash{{background:#1f2d1f;border:1px solid #3fb950;color:#3fb950;
        padding:.4rem .8rem;margin-bottom:1rem;border-radius:4px;font-size:.82rem}}
.flash.warn{{background:#2d2510;border-color:#d29922;color:#d29922}}
.si{{background:#0d1117;color:#c9d1d9;border:1px solid #30363d;padding:.15rem .3rem;
     width:5rem;font:13px "Courier New",monospace;border-radius:3px}}
@media(max-width:600px){{.grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<h1>&#9881; shipobs-server / admin</h1>
{flash}
<div class="topbar">
  <span>updated: {generated}</span>
  <span>auto-refresh:&nbsp;<select id="rsel" onchange="setR(this.value)">
    <option value="0">off</option>
    <option value="5">5 s</option>
    <option value="10">10 s</option>
    <option value="30">30 s</option>
    <option value="60">60 s</option>
  </select></span>
</div>

<div class="grid">
  <div class="card">
    <h2>Server</h2>
    <table class="info">
      <tr><td class="lbl">uptime</td><td class="value">{uptime}</td></tr>
      <tr><td class="lbl">stations</td><td><span class="big">{total_stations}</span></td></tr>
      <tr><td class="lbl">oldest obs</td><td class="ts" style="text-align:left">{oldest}</td></tr>
    </table>
  </div>
  <div class="card">
    <h2>Sources</h2>
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
        oldest=oldest or "—",
        sources_html=_sources_html(sources),
        total_requests=total_requests,
        country_html=_country_html(by_country, total_requests),
        settings_html=_settings_html(
            port,
            settings.osmc_fetch_interval,
            settings.ndbc_fetch_interval,
            settings.max_obs_age_hours,
        ),
    )
