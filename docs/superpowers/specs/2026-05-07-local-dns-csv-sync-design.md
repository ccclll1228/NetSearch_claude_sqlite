# Local DNS CSV Sync — Design Spec
**Date:** 2026-05-07

## Overview

Add on-premise local DNS records from CSV files (Windows PowerShell DNS export)
into `db/fqdn.db` as a new `local_dns` table, alongside the existing `fqdn` table
(populated by `ultradns.py`). All new code is strictly additive — no existing files
are modified except `lib/fqdn_db.js` and `server.js` (append-only changes).

---

## Constraints

- DO NOT modify `ultradns.py`
- DO NOT modify the existing `fqdn` table schema
- DO NOT remove or rename existing functions in `lib/fqdn_db.js`
- DO NOT remove or rename existing API routes in `server.js`
- DO NOT modify `public/index.html`
- ONLY ADD new code

---

## New SQLite Table

```sql
CREATE TABLE IF NOT EXISTS local_dns (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  source_file TEXT,
  zone_name   TEXT,
  host_name   TEXT,
  record_type TEXT,
  record_data TEXT,
  synced_at   TEXT
);
```

Created by both `local_dns_sync.py` (Python `CREATE TABLE IF NOT EXISTS`) and
`lib/fqdn_db.js` (`db.exec(...)` before prepared statements) — both are idempotent.

---

## Deliverable 1 — `local_dns_sync.py` (new file)

**Pattern:** mirrors `ultradns.py` structure.

- `load_dotenv()` at top; `DB_PATH` resolved via `os.path.dirname(os.path.abspath(__file__))`
- `ensure_table(conn)` — `CREATE TABLE IF NOT EXISTS local_dns (...)`
- Dynamic file discovery: `glob.glob(os.path.join(script_dir, "local_dns_csv", "*.csv"))`
- Per-file loop:
  - `try/except`: if file is unreadable, print warning to stderr and `continue`
  - Open with `encoding="utf-8-sig"` (handles BOM transparently)
  - Parse with `csv.DictReader`, columns: `ZoneName`, `HostName`, `RecordType`, `RecordData`
  - Skip rows where all four fields are empty/whitespace
  - One `synced_at = datetime.now(timezone.utc).isoformat()` per file
  - Atomic transaction: `DELETE WHERE source_file = ?` then `executemany INSERT`
  - Print: `filename | N rows | X.XXs`

---

## Deliverable 2 — `lib/fqdn_db.js` (append-only)

**Before** existing prepared statements, add:

```js
db.exec(`CREATE TABLE IF NOT EXISTS local_dns (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  source_file TEXT,
  zone_name   TEXT,
  host_name   TEXT,
  record_type TEXT,
  record_data TEXT,
  synced_at   TEXT
)`);
```

**After** existing code, add two prepared statements and two functions:

- `searchLocalDns(keyword, limit = 200)` — `LIKE %keyword%` on `zone_name`, `host_name`, `record_data`
- `getLocalDnsLastSynced()` — `SELECT synced_at FROM local_dns ORDER BY id DESC LIMIT 1`

**`module.exports`** updated to include both new functions alongside existing ones.

---

## Deliverable 3 — `server.js` (append-only)

Updated import destructure (top of file) to add `searchLocalDns`, `getLocalDnsLastSynced`.

New route appended after existing `/api/fqdn`:

```
GET /api/local_dns?q=<keyword>&limit=<n>
```

- Empty query returns `[]` (intentional — no full-table dump)
- Response shape: `{ results, lastSynced, total }`

---

## Deliverable 4 — `sync_all.sh` (new file)

```bash
#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "=== Step 1: UltraDNS sync ==="
python3 ultradns.py
echo "=== Step 2: Local DNS CSV sync ==="
python3 local_dns_sync.py
```

`chmod +x sync_all.sh`. `set -e` stops execution if `ultradns.py` fails.

---

## Deliverable 5 — `README.md` (append)

New section **"Local DNS CSV Sync"** added after the FQDN Tab section, documenting:
- CSV folder: `local_dns_csv/`
- Imported vs ignored columns
- Manual run commands
- `sync_all.sh` usage
- Crontab example
- `/api/local_dns` endpoint description
