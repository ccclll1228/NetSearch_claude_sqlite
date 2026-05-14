#!/usr/bin/env python3
import csv, sqlite3, glob, os, sys
from datetime import datetime, timezone

DB_PATH = '/home/local/SSO/yt0115/NetSearch_sqlite/db/fqdn.db'
CSV_DIR = '/home/local/SSO/yt0115/NetSearch_sqlite/local_dns_csv'

HIDDEN_DOMAINS = {
    'trz.prd',
    'trz.uat',
    'sso.trz',
    'in-addr.arpa',
}

HIDDEN_TYPES = {
    'PTR',
    'SOA',
    'WINS',
}

def is_hidden(fqdn: str) -> bool:
    fqdn = fqdn.lower()
    for suffix in HIDDEN_DOMAINS:
        if fqdn == suffix or fqdn.endswith('.' + suffix):
            return True
    return False


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
                zone    = row.get('Zone',     '').strip()
                host    = row.get('HostName', '').strip()
                rtype   = row.get('Type',     '').strip().upper()
                rdata   = row.get('Data',     '').strip()
                ttl_raw = row.get('TTL',      '').strip()
                dns_srv = row.get('Server',   '').strip()

                if rtype in HIDDEN_TYPES:
                    continue

                # Build FQDN
                if host == '@' or host == '':
                    fqdn = zone
                else:
                    fqdn = f"{host}.{zone}"

                if is_hidden(fqdn):
                    continue

                ip = rdata
                ttl = int(ttl_raw) if ttl_raw.isdigit() else None

                rows.append((fqdn, ip, 'localDNS', zone, rtype, ttl, None, now))

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

    all_csv   = sorted(glob.glob(os.path.join(CSV_DIR, '*.csv')))
    csv_files = [all_csv[-1]] if all_csv else []
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
