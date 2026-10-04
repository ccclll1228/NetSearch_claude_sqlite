#!/usr/bin/env python3
"""Read Cloudflare DNS-only records into NetSearch's db/fqdn.db.

Install: python3 -m pip install requests python-dotenv
Put this file in the NetSearch project root. In the adjacent .env:
    CLOUDFLARE_API_TOKEN=your_read_only_token
    CLOUDFLARE_ACCOUNT_ID=optional_account_id
Token permissions: Zone / Zone / Read and Zone / DNS / Read for the intended
zones. No Cloudflare write requests are made.

Usage:
    python3 cloudflare_dns.py --dry-run
    python3 cloudflare_dns.py
    python3 cloudflare_dns.py --zone example.com --zone example.net
    python3 cloudflare_dns.py --db /absolute/path/db/fqdn.db

All selected zones must be fetched and validated before any DB change. A single
SQLite transaction replaces ONLY owner='Cloudflare' rows in the fetched zones.
UltraDNS, local DNS, and Cloudflare zones outside the selected/visible scope are
preserved. Deleted/inaccessible zones are not automatically purged. In migration,
stop ultradns.py before scheduling this script: that old script deletes the whole
fqdn table. Remove obsolete UltraDNS rows separately after verifying the cutover.

One API record becomes one DB row; multiple A records stay separate. The historic
'ip' column stores record content (not always an IP). CNAME/NS/PTR targets are
stored without their final dot; no live DNS lookup or CNAME-chain resolution is
performed. MX includes priority; SRV includes priority/weight/port/target. Long
TXT records are kept. ttl=1 is Cloudflare Auto, NOT a one-second effective TTL.
Zone name_servers are also stored as apex NS rows with ttl=NULL, since the zone
metadata does not supply a TTL. Matching DNS-record NS rows retain their TTL;
child delegations are preserved. These are assigned nameservers, not proof that
the registrar has switched delegation. original_name_servers are not imported.
geo_info is empty: this script does not collect Load Balancer pools or GEO policy.
Proxied records abort the sync because this deployment is explicitly DNS-only.

Official references (checked 2026-10-04):
https://developers.cloudflare.com/api/resources/zones/methods/list/
https://developers.cloudflare.com/api/resources/dns/subresources/records/methods/list/
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import ipaddress
import logging
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
from typing import Any, Iterator

import requests

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # Exported environment variables also work without dotenv.

BASE_URL = "https://api.cloudflare.com/client/v4"
OWNER = "Cloudflare"
ROOT = Path(__file__).resolve().parent
LOG = logging.getLogger("cloudflare_dns")


class SyncError(RuntimeError):
    """A failed or incomplete sync; the database must not be replaced."""


def integer(value: Any, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise SyncError(f"Invalid {label}: expected integer >= {minimum}")
    return value


def dns_name(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SyncError("Missing DNS name")
    name = value.strip().rstrip(".").lower()
    try:
        return name.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise SyncError("Invalid DNS name") from exc


def identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{32}", value):
        raise SyncError(f"Invalid {label}: expected 32-character hexadecimal ID")
    return value


class CloudflareClient:
    """Sequential, rate-paced GET requests; one session, no shared-thread state."""

    def __init__(self, token: str, retries: int = 4, interval: float = 0.3):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "NetSearch-Cloudflare-DNS-Sync/1.0",
        })
        self.retries = retries
        self.interval = interval
        self.last_request = 0.0

    def close(self) -> None:
        self.session.close()

    @staticmethod
    def retry_delay(header: str | None, attempt: int) -> float:
        if header:
            try:
                return max(0.0, float(header))
            except ValueError:
                try:
                    date = parsedate_to_datetime(header)
                    if date.tzinfo is None:
                        date = date.replace(tzinfo=timezone.utc)
                    return max(0.0, (date - datetime.now(timezone.utc)).total_seconds())
                except (ValueError, TypeError, OverflowError):
                    pass
        return min(60.0, 2.0 ** attempt)

    def get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(self.retries + 1):
            wait = self.interval - (time.monotonic() - self.last_request)
            if wait > 0:
                time.sleep(wait)
            self.last_request = time.monotonic()
            try:
                response = self.session.get(
                    BASE_URL + path, params=params, timeout=(10, 60),
                    allow_redirects=False,
                )
            except requests.RequestException:
                if attempt == self.retries:
                    raise SyncError(f"{path}: network failure after retries") from None
                LOG.warning("%s: network error; retry %d/%d", path, attempt + 1, self.retries)
                time.sleep(self.retry_delay(None, attempt))
                continue

            if response.status_code == 429 or response.status_code in (500, 502, 503, 504):
                status = response.status_code
                delay = self.retry_delay(response.headers.get("Retry-After"), attempt)
                response.close()
                if attempt == self.retries:
                    raise SyncError(f"{path}: HTTP {status} after retries")
                LOG.warning("%s: HTTP %d; retry in %.1fs", path, status, delay)
                time.sleep(delay)
                continue
            try:
                if not 200 <= response.status_code < 300:
                    # Do not print raw responses or authorization headers.
                    raise SyncError(f"{path}: HTTP {response.status_code}; check token permissions")
                try:
                    payload = response.json()
                except ValueError:
                    raise SyncError(f"{path}: invalid JSON response") from None
                if not isinstance(payload, dict) or payload.get("success") is not True:
                    raise SyncError(f"{path}: API success flag is not true")
                return payload
            finally:
                response.close()
        raise SyncError(f"{path}: retries exhausted")

    def paginated(self, path: str, per_page: int,
                  params: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
        page, received = 1, 0
        expected_total = None
        expected_pages = None
        seen_ids: set[str] = set()
        while True:
            payload = self.get(path, {**(params or {}), "page": page, "per_page": per_page})
            items = payload.get("result")
            info = payload.get("result_info")
            if not isinstance(items, list) or not isinstance(info, dict):
                raise SyncError(f"{path}: missing result/result_info")
            if integer(info.get("page"), "page", 1) != page:
                raise SyncError(f"{path}: unexpected response page")
            actual_page_size = integer(info.get("per_page"), "per_page", 1)
            if len(items) > actual_page_size:
                raise SyncError(f"{path}: page exceeds reported page size")
            if "count" in info and integer(info["count"], "count") != len(items):
                raise SyncError(f"{path}: inconsistent page count")
            if "total_count" in info:
                total = integer(info["total_count"], "total_count")
                if expected_total is not None and total != expected_total:
                    raise SyncError(f"{path}: data changed during pagination; rerun sync")
                expected_total = total
            if "total_pages" in info:
                pages = integer(info["total_pages"], "total_pages")
                if expected_pages is not None and pages != expected_pages:
                    raise SyncError(f"{path}: page total changed; rerun sync")
                expected_pages = pages
            for item in items:
                if not isinstance(item, dict):
                    raise SyncError(f"{path}: invalid result entry")
                item_id = identifier(item.get("id"), "result ID")
                if item_id in seen_ids:
                    raise SyncError(f"{path}: repeated result ID; pagination is inconsistent")
                seen_ids.add(item_id)
                received += 1
                yield item
            if expected_total is not None and received > expected_total:
                raise SyncError(f"{path}: more results than reported")
            if expected_pages is not None:
                done = page >= max(1, expected_pages)
            elif expected_total is not None:
                done = received == expected_total
            else:
                done = len(items) < actual_page_size
            if done:
                if expected_total is not None and received != expected_total:
                    raise SyncError(f"{path}: incomplete result ({received}/{expected_total})")
                return
            if not items:
                raise SyncError(f"{path}: empty page before end of results")
            page += 1


def parse_record(record: dict[str, Any], zone: str) -> dict[str, Any]:
    fqdn = dns_name(record.get("name"))
    if fqdn != zone and not fqdn.endswith("." + zone):
        raise SyncError(f"{fqdn}: record is outside zone {zone}")
    kind = record.get("type")
    if not isinstance(kind, str) or not kind:
        raise SyncError(f"{fqdn}: missing record type")
    kind = kind.upper()
    ttl = integer(record.get("ttl"), "TTL", 1)
    if record.get("proxied") is True:
        raise SyncError(f"{fqdn}: proxied record found; this sync expects DNS Only")
    content = record.get("content")
    data = record.get("data") or {}
    if kind == "SRV" and isinstance(data, dict) and all(
        field in data for field in ("priority", "weight", "port", "target")
    ):
        content = "{} {} {} {}".format(
            integer(data["priority"], "SRV priority"),
            integer(data["weight"], "SRV weight"),
            integer(data["port"], "SRV port"),
            dns_name(data["target"]) if data["target"] != "." else ".",
        )
    if not isinstance(content, str) or not content:
        raise SyncError(f"{fqdn} {kind}: missing record content")
    if kind in ("A", "AAAA"):
        try:
            addr = ipaddress.ip_address(content)
        except ValueError:
            raise SyncError(f"{fqdn} {kind}: invalid IP address") from None
        if addr.version != (4 if kind == "A" else 6):
            raise SyncError(f"{fqdn}: IP family does not match {kind}")
        content = str(addr)
    elif kind in ("CNAME", "NS", "PTR"):
        content = dns_name(content)
    elif kind == "MX":
        priority = integer(record.get("priority"), "MX priority")
        content = f"{priority} {dns_name(content)}"
    # Other content is retained verbatim, including long TXT values.
    return {"fqdn": fqdn, "ip": content, "owner": OWNER, "domain": zone,
            "type": kind, "ttl": ttl, "geo_info": ""}


def parse_nameservers(entry: dict[str, Any], zone: str) -> list[dict[str, Any]]:
    """Convert assigned zone nameservers into apex NS rows without inventing TTL."""
    nameservers = entry.get("name_servers")
    if not isinstance(nameservers, list):
        raise SyncError(f"{zone}: missing or invalid name_servers in zone response")
    targets: set[str] = set()
    for value in nameservers:
        target = dns_name(value)
        if not target or any(char.isspace() for char in target):
            raise SyncError(f"{zone}: invalid assigned nameserver")
        targets.add(target)
    return [{"fqdn": zone, "ip": target, "owner": OWNER, "domain": zone,
             "type": "NS", "ttl": None, "geo_info": ""}
            for target in sorted(targets)]


def collect(client: CloudflareClient, account_id: str | None,
            requested_zones: list[str], allow_empty: bool = False
            ) -> tuple[list[str], list[dict[str, Any]]]:
    params: dict[str, Any] = {"order": "name", "direction": "asc"}
    if account_id:
        params["account.id"] = account_id
    zones = list(client.paginated("/zones", 50, params))
    wanted = {dns_name(name) for name in requested_zones}
    selected: dict[str, tuple[str, list[dict[str, Any]]]] = {}
    for entry in zones:
        name = dns_name(entry.get("name"))
        if wanted and name not in wanted:
            continue
        if name in selected:
            raise SyncError(f"Duplicate zone name {name}; narrow scope with --account-id")
        selected[name] = (identifier(entry.get("id"), "zone ID"),
                          parse_nameservers(entry, name))
    missing = wanted - selected.keys()
    if missing:
        raise SyncError("Requested zones not visible to token: " + ", ".join(sorted(missing)))
    if not selected:
        raise SyncError("No zones selected/visible; database preserved")
    LOG.info("Fetching records from %d zone(s)", len(selected))
    records: list[dict[str, Any]] = []
    for index, (zone, (zone_id, nameserver_rows)) in enumerate(sorted(selected.items()), 1):
        zone_records = [parse_record(r, zone) for r in client.paginated(
            f"/zones/{zone_id}/dns_records", 1000,
            {"order": "name", "direction": "asc"},
        )]
        if not zone_records and not allow_empty:
            raise SyncError(f"{zone}: zero records; use --allow-empty-zones only if intentional")
        # Check the raw DNS-record result above, before adding metadata rows:
        # assigned nameservers must not hide an unexpectedly empty DNS response.
        seen_ns: set[tuple[str, str, str]] = set()
        merged: list[dict[str, Any]] = []
        added_nameservers = 0
        for row in zone_records + nameserver_rows:
            if row["type"] == "NS":
                key = (row["fqdn"], row["type"], row["ip"])
                if key in seen_ns:
                    continue
                seen_ns.add(key)
                if row["ttl"] is None:
                    added_nameservers += 1
            merged.append(row)
        records.extend(merged)
        LOG.info("[%d/%d] %s: %d DNS records + %d assigned nameservers added; %d rows",
                 index, len(selected), zone, len(zone_records), added_nameservers, len(merged))
    return sorted(selected), records


def write_to_db(db_path: Path, zones: list[str], records: list[dict[str, Any]],
                synced_at: str) -> None:
    if not zones:
        raise SyncError("Refusing database write without a zone scope")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30, isolation_level=None)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""CREATE TABLE IF NOT EXISTS fqdn (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fqdn TEXT, ip TEXT, owner TEXT, domain TEXT, type TEXT,
            ttl INTEGER, geo_info TEXT, synced_at TEXT
        )""")
        columns = {row[1] for row in conn.execute("PRAGMA table_info(fqdn)")}
        required = {"id", "fqdn", "ip", "owner", "domain", "type", "ttl", "geo_info", "synced_at"}
        if not required <= columns:
            raise SyncError("Existing fqdn schema is incompatible; database preserved")
        conn.executemany("DELETE FROM fqdn WHERE owner = ? AND domain = ?",
                         [(OWNER, zone) for zone in zones])
        conn.executemany("""INSERT INTO fqdn
            (fqdn, ip, owner, domain, type, ttl, geo_info, synced_at)
            VALUES (:fqdn, :ip, :owner, :domain, :type, :ttl, :geo_info, :synced_at)""",
            ({**record, "synced_at": synced_at} for record in records))
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    if load_dotenv is not None:
        load_dotenv(ROOT / ".env")  # Environment wins; not dependent on cron cwd.
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", type=Path, default=ROOT / "db" / "fqdn.db")
    parser.add_argument("--account-id", default=os.getenv("CLOUDFLARE_ACCOUNT_ID"))
    parser.add_argument("--zone", action="append", default=[], help="Exact zone name; repeat for several zones")
    parser.add_argument("--dry-run", action="store_true", help="Fetch/validate without writing files or SQLite")
    parser.add_argument("--allow-empty-zones", action="store_true", help="Allow replacing selected zones with zero records")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    if not token:
        LOG.error("CLOUDFLARE_API_TOKEN is not set")
        return 1
    client = None
    lock_file = None
    started = time.monotonic()
    try:
        if args.account_id:
            identifier(args.account_id, "account ID")
        db_path = args.db.expanduser().resolve()
        if not args.dry_run:
            # Linux server: prevent overlapping cron/manual runs, including fetching.
            try:
                import fcntl
            except ImportError:
                raise SyncError("Write mode requires Linux/Unix flock; --dry-run works on Windows") from None
            db_path.parent.mkdir(parents=True, exist_ok=True)
            lock_file = open(str(db_path) + ".cloudflare-sync.lock", "a", encoding="utf-8")
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise SyncError("Another Cloudflare sync is already running") from None
        client = CloudflareClient(token)
        zones, records = collect(client, args.account_id, args.zone, args.allow_empty_zones)
        LOG.info("Validated %d records; types=%s", len(records), dict(Counter(r["type"] for r in records)))
        if args.dry_run:
            LOG.info("DRY RUN: database unchanged")
        else:
            synced_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            write_to_db(db_path, zones, records, synced_at)
            LOG.info("Committed to %s; owner=%s, zones=%d", db_path, OWNER, len(zones))
        LOG.info("Sync complete in %.1fs", time.monotonic() - started)
        return 0
    except (SyncError, sqlite3.Error, OSError) as exc:
        # Token redaction also covers unexpected server-provided names.
        LOG.error("Sync failed: %s", str(exc).replace(token, "[REDACTED]"))
        return 1
    except KeyboardInterrupt:
        LOG.error("Sync interrupted")
        return 130
    finally:
        if client is not None:
            client.close()
        if lock_file is not None:
            lock_file.close()


if __name__ == "__main__":
    sys.exit(main())

