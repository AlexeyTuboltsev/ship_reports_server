from __future__ import annotations

import ipaddress
from collections import Counter

_total_requests: int = 0
_country_counts: Counter[str] = Counter()  # finalized per-country counts
_ip_hit_count: Counter[str] = Counter()    # hits from IPs not yet geo-resolved
_ip_country_cache: dict[str, str] = {}     # ip -> country code (never exposed)
_pending_lookups: set[str] = set()         # IPs with an in-flight lookup


def _is_private(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
        return addr.is_loopback or addr.is_private or addr.is_link_local
    except ValueError:
        return True


def record_hit(ip: str) -> bool:
    """Record one API hit for this IP.

    Returns True if the caller should trigger an async GeoIP lookup for this IP.
    """
    global _total_requests
    _total_requests += 1

    if _is_private(ip):
        _country_counts["Local"] += 1
        return False

    if ip in _ip_country_cache:
        _country_counts[_ip_country_cache[ip]] += 1
        return False

    # Not yet resolved — buffer the hit
    _ip_hit_count[ip] += 1
    if ip not in _pending_lookups:
        _pending_lookups.add(ip)
        return True  # trigger lookup
    return False


def update_country(ip: str, country: str) -> None:
    """Move all buffered hits for this IP into its resolved country bucket."""
    _pending_lookups.discard(ip)
    if ip in _ip_country_cache:
        return  # already resolved by a concurrent lookup
    _ip_country_cache[ip] = country
    hits = _ip_hit_count.pop(ip, 0)
    if hits:
        _country_counts[country] += hits


def get_stats() -> dict:
    combined: Counter[str] = Counter(_country_counts)
    pending_hits = sum(_ip_hit_count.values())
    if pending_hits:
        combined["Pending"] += pending_hits
    return {
        "total_requests": _total_requests,
        "by_country": dict(combined.most_common(20)),
    }
