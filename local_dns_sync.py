#!/usr/bin/env python3
"""
local_dns_sync.py — Import on-premise local DNS records from CSV files into db/fqdn.db.

Usage:
  python3 local_dns_sync.py

CSV files must be placed in: local_dns_csv/*.csv
Expected columns: ZoneName, HostName, RecordType, RecordData
"""

import csv
import glob
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

script_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH    = os.path.join(script_dir, "db", "fqdn.db")
CSV_DIR    = os.path.join(script_dir, "local_dns_csv")


def ensure_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS local_dns (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source_file TEXT,
            zone_name   TEXT,
            host_name   TEXT,
            record_type TEXT,
            record_data TEXT,
            synced_at   TEXT
        )
    """)
    conn.commit()


def sync_file(conn, csv_path):
    filename   = os.path.basename(csv_path)
    t_start    = time.time()
    synced_at  = datetime.now(timezone.utc).isoformat()

    try:
        with open(csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                zone    = (row.get("ZoneName")    or "").strip()
                host    = (row.get("HostName")     or "").strip()
                rtype   = (row.get("RecordType")   or "").strip()
                rdata   = (row.get("RecordData")   or "").strip()
                if not zone and not host and not rtype and not rdata:
                    continue
                rows.append((filename, zone, host, rtype, rdata, synced_at))
    except Exception as exc:
        print(f"  [warning] Could not read {filename}: {exc}", file=sys.stderr)
        return

    try:
        conn.execute("BEGIN")
        conn.execute("DELETE FROM local_dns WHERE source_file = ?", (filename,))
        conn.executemany(
            "INSERT INTO local_dns (source_file, zone_name, host_name, record_type, record_data, synced_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.execute("COMMIT")
    except Exception as exc:
        conn.execute("ROLLBACK")
        print(f"  [error] DB write failed for {filename}: {exc}", file=sys.stderr)
        return

    elapsed = time.time() - t_start
    print(f"  {filename} | {len(rows)} rows | {elapsed:.2f}s", flush=True)


def main():
    print("=== Local DNS CSV → SQLite sync ===", flush=True)

    csv_files = sorted(glob.glob(os.path.join(CSV_DIR, "*.csv")))
    if not csv_files:
        print(f"No CSV files found in {CSV_DIR}/", flush=True)
        return

    print(f"Found {len(csv_files)} CSV file(s) in local_dns_csv/", flush=True)

    conn = sqlite3.connect(DB_PATH, isolation_level=None)
    try:
        ensure_table(conn)
        for csv_path in csv_files:
            sync_file(conn, csv_path)
    finally:
        conn.close()

    print("=== Sync complete ===", flush=True)


if __name__ == "__main__":
    main()
