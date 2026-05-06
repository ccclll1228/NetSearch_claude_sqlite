#!/usr/bin/env python3
"""
ultradns.py — Full sync of all UltraDNS rrSets into db/fqdn.db (SQLite).

Usage:
  export ULTRADNS_USERNAME=...
  export ULTRADNS_PASSWORD=...
  python3 ultradns.py
"""

import asyncio
import os
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

AUTH_URL    = "https://api.ultradns.com/authorization/token"
BASE_URL    = "https://api.ultradns.com"
DB_PATH     = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db", "fqdn.db")
MAX_WORKERS = 20


# ── Authentication ────────────────────────────────────────────────────────────

def get_token() -> str:
    username = os.environ.get("ULTRADNS_USERNAME")
    password = os.environ.get("ULTRADNS_PASSWORD")
    if not username:
        print("Error: ULTRADNS_USERNAME is not set.", file=sys.stderr)
        sys.exit(1)
    if not password:
        print("Error: ULTRADNS_PASSWORD is not set.", file=sys.stderr)
        sys.exit(1)

    resp = requests.post(
        AUTH_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "password", "username": username, "password": password},
        timeout=30,
    )
    if not (200 <= resp.status_code < 300):
        print(f"Auth failed: HTTP {resp.status_code} — {resp.text[:300]}", file=sys.stderr)
        sys.exit(1)

    token = resp.json().get("accessToken", "")
    if not token:
        print("Auth failed: API did not return accessToken.", file=sys.stderr)
        sys.exit(1)

    return token


# ── Zone list ─────────────────────────────────────────────────────────────────

def get_all_zones(token: str) -> list[str]:
    """Return all zone names (without trailing dot), skipping any containing 'sanbox'."""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    zones: list[str] = []
    limit  = 500
    offset = 0

    while True:
        url  = f"{BASE_URL}/zones?limit={limit}&offset={offset}"
        resp = requests.get(url, headers=headers, timeout=30)
        if not (200 <= resp.status_code < 300):
            print(f"Zone list failed: HTTP {resp.status_code} — {resp.text[:300]}", file=sys.stderr)
            sys.exit(1)

        data        = resp.json()
        result_info = data.get("resultInfo", {})
        zone_list   = data.get("zones", [])

        for z in zone_list:
            name = z.get("properties", {}).get("name", "") or z.get("name", "")
            if not name:
                continue
            if "sanbox" in name.lower():
                continue
            zones.append(name.rstrip("."))

        returned = result_info.get("returnedCount", len(zone_list))
        total    = result_info.get("totalCount", returned)
        offset  += returned
        if offset >= total or returned == 0:
            break

    return zones


# ── Record parsing ────────────────────────────────────────────────────────────

def _parse_rrset(rrset: dict, zone_clean: str) -> list[dict]:
    """
    Parse one rrset dict into a list of record dicts ready for DB insert.
    Matches the original Flask logic exactly:
      - Profile (geo) records: one row per rdataInfo entry, ttl/type from rdataInfo
      - Non-profile records:   one row per rrset, rdata joined with ","
      - Skip NS (2), SOA (6)
      - Skip TXT longer than 255 chars after join
      - Skip ownerName containing sanbox888.com._domainkey
    """
    owner_name = rrset.get("ownerName", "")

    # ownerName from UltraDNS is absolute (ends with "."); strip trailing dot
    fqdn    = owner_name.rstrip(".")
    rdata   = rrset.get("rdata", [])
    profile = rrset.get("profile")
    rrtype  = rrset.get("rrtype", "")

    # ── Profile (geo / IP-pool) records ──────────────────────────────────────
    # Identified by presence of "profile" key AND absence of "ttl" at rrset level
    if profile and "ttl" not in rrset:
        records = []
        for value, info in zip(rdata, profile.get("rdataInfo", [])):
            if "geoInfo" in info:
                geo_info = info["geoInfo"].get("name", "")
            elif "allNonConfigured" in info:
                geo_info = "allNonConfigured"
            elif "ipInfo" in info:
                geo_info = info["ipInfo"].get("name", "")
            else:
                geo_info = ""
            records.append({
                "fqdn":     fqdn,
                "ip":       value,
                "owner":    "ultraDNS",
                "domain":   zone_clean,
                "type":     info.get("type", ""),
                "ttl":      info.get("ttl"),
                "geo_info": geo_info,
            })
        return records

    # ── Standard (non-profile) records ───────────────────────────────────────
    ttl = rrset.get("ttl")

    if "(1)" in rrtype:          # A
        return [{
            "fqdn":     fqdn,
            "ip":       ",".join(rdata),
            "owner":    "ultraDNS",
            "domain":   zone_clean,
            "type":     "A",
            "ttl":      ttl,
            "geo_info": "",
        }]

    if "(5)" in rrtype:          # CNAME
        return [{
            "fqdn":     fqdn,
            "ip":       ",".join(rdata),
            "owner":    "ultraDNS",
            "domain":   zone_clean,
            "type":     "CNAME",
            "ttl":      ttl,
            "geo_info": "",
        }]

    if "(15)" in rrtype:         # MX
        return [{
            "fqdn":     fqdn,
            "ip":       ",".join(rdata),
            "owner":    "ultraDNS",
            "domain":   zone_clean,
            "type":     "MX",
            "ttl":      ttl,
            "geo_info": "",
        }]

    if "(16)" in rrtype:         # TXT
        txt_string = ",".join(rdata)
        if len(txt_string) > 255:
            return []
        return [{
            "fqdn":     fqdn,
            "ip":       txt_string,
            "owner":    "ultraDNS",
            "domain":   zone_clean,
            "type":     "TXT",
            "ttl":      ttl,
            "geo_info": "",
        }]

    if "(99)" in rrtype:         # SPF
        spf_string = ",".join(rdata)
        if len(spf_string) > 255:
            return []
        return [{
            "fqdn":     fqdn,
            "ip":       spf_string,
            "owner":    "ultraDNS",
            "domain":   zone_clean,
            "type":     "SPF",
            "ttl":      ttl,
            "geo_info": "",
        }]

    if "(65282)" in rrtype:      # APEXALIAS
        return [{
            "fqdn":     fqdn,
            "ip":       ",".join(rdata),
            "owner":    "ultraDNS",
            "domain":   zone_clean,
            "type":     "APEXALIAS",
            "ttl":      ttl,
            "geo_info": "",
        }]

    # (2) NS and (6) SOA are silently skipped; anything else is logged
    if "(2)" not in rrtype and "(6)" not in rrtype:
        print(f"  [unhandled] {fqdn} {rrtype}", flush=True)

    return []


def fetch_zone_records(zone: str, token: str) -> list[dict]:
    """Fetch all rrsets for one zone with pagination. Returns list of record dicts."""
    headers    = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    zone_clean = zone.rstrip(".")
    records: list[dict] = []
    limit  = 500
    offset = 0

    while True:
        url = f"{BASE_URL}/zones/{zone}/rrsets?limit={limit}&offset={offset}"
        try:
            resp = requests.get(url, headers=headers, timeout=60)
        except Exception as exc:
            print(f"  [{zone}] request error: {exc}", flush=True)
            return records

        if not (200 <= resp.status_code < 300):
            print(f"  [{zone}] HTTP {resp.status_code} — {resp.text[:200]}", flush=True)
            return records

        try:
            data = resp.json()
        except Exception as exc:
            print(f"  [{zone}] JSON decode error: {exc}", flush=True)
            return records

        for rrset in data.get("rrSets", []):
            records.extend(_parse_rrset(rrset, zone_clean))

        result_info = data.get("resultInfo", {})
        returned    = result_info.get("returnedCount", len(data.get("rrSets", [])))
        total       = result_info.get("totalCount", returned)
        offset     += returned
        if offset >= total or returned == 0:
            break

    return records


# ── Async orchestration ───────────────────────────────────────────────────────

async def fetch_all_zones_async(zones: list[str], token: str) -> tuple[list[dict], int]:
    loop        = asyncio.get_running_loop()
    n           = len(zones)
    all_records: list[dict] = []
    errors      = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        tasks   = [loop.run_in_executor(executor, fetch_zone_records, z, token) for z in zones]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, (zone, result) in enumerate(zip(zones, results), 1):
        if isinstance(result, Exception):
            errors += 1
            print(f"  [{i}/{n}] {zone}: ERROR — {result}", flush=True)
        else:
            all_records.extend(result)
            print(f"  [{i}/{n}] {zone}: {len(result)} records", flush=True)

    return all_records, errors


# ── SQLite write ──────────────────────────────────────────────────────────────

def write_to_db(records: list[dict], synced_at: str) -> None:
    conn = sqlite3.connect(DB_PATH, isolation_level=None)  # manual transaction control
    try:
        conn.execute("BEGIN")
        conn.execute("DELETE FROM fqdn")
        conn.executemany(
            """INSERT INTO fqdn (fqdn, ip, owner, domain, type, ttl, geo_info, synced_at)
               VALUES (:fqdn, :ip, :owner, :domain, :type, :ttl, :geo_info, :synced_at)""",
            [{**r, "synced_at": synced_at} for r in records],
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    t_start = time.time()
    print("=== UltraDNS → SQLite sync ===", flush=True)

    print("Authenticating...", flush=True)
    token = get_token()
    print(f"Token obtained. ({time.time() - t_start:.1f}s)", flush=True)

    print("Fetching zone list...", flush=True)
    t1    = time.time()
    zones = get_all_zones(token)
    print(f"{len(zones)} zones loaded. ({time.time() - t1:.1f}s)", flush=True)

    print(f"Fetching rrSets for {len(zones)} zones (workers={MAX_WORKERS})...", flush=True)
    t2 = time.time()
    all_records, errors = asyncio.run(fetch_all_zones_async(zones, token))
    print(
        f"rrSets done: {len(all_records)} records, {errors} zone error(s). "
        f"({time.time() - t2:.1f}s)",
        flush=True,
    )

    synced_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"Writing {len(all_records)} records to SQLite (synced_at={synced_at})...", flush=True)
    t3 = time.time()
    write_to_db(all_records, synced_at)
    print(f"DB write done. ({time.time() - t3:.1f}s)", flush=True)

    total = time.time() - t_start
    print(f"=== Sync complete: {len(all_records)} records in {total:.1f}s ===", flush=True)


if __name__ == "__main__":
    main()
