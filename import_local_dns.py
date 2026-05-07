#!/usr/bin/env python3
import csv, sqlite3, glob, os, sys
from datetime import datetime, timezone

DB_PATH = '/home/local/SSO/yt0115/NetSearch_sqlite/db/fqdn.db'
CSV_DIR = '/home/local/SSO/yt0115/NetSearch_sqlite/local_dns_csv'


def ensure_table(conn):
    """Verify the fqdn table is accessible before processing any files."""
    conn.execute("SELECT 1 FROM fqdn LIMIT 1")


def sync_file(conn, csv_path, now):
    """Parse one CSV file and insert its rows into fqdn. Returns row count."""
    try:
        with open(csv_path, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = []
            for row in reader:
                zone    = row.get('ZoneName',    '').strip()
                host    = row.get('HostName',     '').strip()
                rtype   = row.get('RecordType',   '').strip()
                rdata   = row.get('RecordData',   '').strip()
                dns_srv = row.get('PSComputerName', '').strip()

                # Build FQDN
                if host == '@' or host == '':
                    fqdn = zone
                else:
                    fqdn = f"{host}.{zone}"

                # ip field: A record fills IP, otherwise original RecordData
                ip = rdata if rtype == 'A' else rdata

                rows.append((fqdn, ip, 'localDNS', zone, rtype, None, None, now))

            conn.executemany(
                "INSERT INTO fqdn (fqdn, ip, owner, domain, type, ttl, geo_info, synced_at) VALUES (?,?,?,?,?,?,?,?)",
                rows,
            )
            print(f"  {os.path.basename(csv_path)}: {len(rows)} rows")
            return len(rows)
    except Exception as exc:
        print(f"  [error] {os.path.basename(csv_path)}: {exc}", file=sys.stderr)
        raise


def main():
    now = datetime.now(timezone.utc).isoformat()

    try:
        conn = sqlite3.connect(DB_PATH)
    except Exception as exc:
        print(f"[error] Cannot open database {DB_PATH}: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        ensure_table(conn)
    except Exception as exc:
        print(f"[error] fqdn table not accessible: {exc}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    # Clear old localDNS rows (no duplicates on re-run)
    conn.execute("DELETE FROM fqdn WHERE owner = 'localDNS'")
    print("Cleared old localDNS rows.")

    csv_files = sorted(glob.glob(os.path.join(CSV_DIR, '*.csv')))
    if not csv_files:
        print(f"No CSV files found in {CSV_DIR}/")
        conn.commit()
        conn.close()
        return

    succeeded = 0
    failed    = 0
    total     = 0

    for csv_path in csv_files:
        try:
            total += sync_file(conn, csv_path, now)
            conn.commit()      # commit this file immediately
            succeeded += 1
        except Exception:
            conn.rollback()    # discard partial writes for this file only
            failed += 1

    conn.close()
    print(f"\nDone. Total inserted: {total}")
    print(f"=== Sync complete: {succeeded} succeeded, {failed} failed ===")


if __name__ == "__main__":
    main()
