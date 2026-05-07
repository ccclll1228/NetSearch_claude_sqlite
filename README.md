# NetSearch

A browser-based network configuration search tool for firewall and load-balancer devices.  
Parse and search across FortiGate, Palo Alto, Juniper SRX, and F5 LTM configurations from a single interface.

---

## Features

- Multi-device support: FortiGate, Palo Alto, Juniper SRX, F5 LTM
- Full-text search with boolean operators (`AND`, `OR`, `NOT`)
- Filter by From Zone / To Zone / Tag / Source / Destination
- Tabs: Sec Rules, NAT Rules, Routes, Objects, LTM VS, Pools, FQDN, Copy, Raw Config, Debug
- Symmetric chaining — find related rules by shared IPs
- FQDN lookup backed by SQLite (`db/fqdn.db`): UltraDNS cloud records via `ultradns.py` and on-premise DNS via `import_local_dns.py` — both merged in the same results table
- Disabled rule dimming, tag badges, resizable NAT columns
- Auto-reload via cron schedule (default: 05:00 and 17:00)
- Parsed data cached to disk; served instantly on restart
- Drag-and-drop config debug mode (browser-only, no server needed)

---

## Requirements

- Node.js 18+
- npm
- Python 3.8+ with `requests` and `python-dotenv` (for `ultradns.py` and `import_local_dns.py`)

---

## Installation

```bash
git clone https://github.com/ccclll1228/NetSearch_claude_sqlite.git
cd NetSearch_claude_sqlite
npm install
```

---

## Configuration

Copy the example config and edit paths to match your environment:

```bash
cp config/settings.example.json config/settings.json
```

`config/settings.json` (not committed — contains local paths):

```json
{
  "port": 3002,
  "backupRoot": "/path/to/oxidized/backups",
  "devices": [
    { "name": "FRI-FW01",  "type": "paloalto" },
    { "name": "FRI-LTM01", "type": "f5" }
  ],
  "fqdnFile": "/path/to/all_fqdn.csv",
  "cronSchedule": ["0 5 * * *", "0 17 * * *"]
}
```

| Field | Description |
|-------|-------------|
| `port` | HTTP port (default: 3002) |
| `backupRoot` | Absolute path to the Oxidized backup root directory |
| `devices[].name` | Device name — also used as the filename prefix to locate the latest backup |
| `devices[].type` | `"fortigate"`, `"paloalto"`, `"srx"`, `"f5"`, or `"auto"` |
| `fqdnFile` | (Legacy) Path to a CSV with columns `fqdn,ip,owner,…` — superseded by SQLite |
| `cronSchedule` | Cron expressions for auto-reload (two entries = twice daily) |

**Discovery** — on every reload, `lib/discovery.js` scans `{backupRoot}/{SITE}_{YYYYMMDD}/` folders (newest first) and picks the file with the highest `HHMM` timestamp. Any path containing `"UCS"` is excluded.

---

## Usage

```bash
# Production
npm start

# Development (auto-restart on file change)
npm run dev
```

Open **http://localhost:3002** in your browser.

### Manual reload via API

```bash
curl -X POST http://localhost:3002/api/reload
curl http://localhost:3002/api/status
```

### Search syntax

| Example | Meaning |
|---------|---------|
| `10.0.0.1` | Match any field containing this IP |
| `"exact-name"` | Exact match |
| `web AND untrust` | Both terms must match |
| `web OR mail` | Either term matches |
| `NOT disabled` | Exclude matches |
| `192.168.1.0/24` | CIDR range match |

---

## File Structure

```
NetSearch_claude_sqlite/
├── server.js                  # Express server, in-memory state, API routes
├── ultradns.py                # UltraDNS → SQLite sync (fqdn table)
├── import_local_dns.py          # Local DNS CSV → SQLite sync (local_dns table)
├── sync_all.sh                # Runs ultradns.py then import_local_dns.py (set -e)
├── package.json
├── CLAUDE.md                  # AI coding guidance
├── ARCHITECTURE.md            # Full data-flow diagrams
├── local_dns_csv/             # Drop per-DNS-server CSV exports here
├── lib/
│   ├── parser.js              # Config parsers (FortiGate, PaloAlto, SRX, F5)
│   ├── scheduler.js           # node-cron auto-reload scheduler
│   ├── discovery.js           # Resolves latest backup file per device
│   └── fqdn_db.js             # SQLite helper: search/searchLocalDns + getLastSynced
├── public/
│   └── index.html             # Single-file frontend (CSS + JS + HTML inline)
├── config/
│   ├── settings.json          # Local config (gitignored)
│   └── settings.example.json  # Template
├── db/
│   └── fqdn.db                # SQLite database (fqdn + local_dns tables, gitignored)
└── cache/
    └── parsed.json            # Auto-generated parse cache (gitignored)
```

---

## Architecture

```
config/settings.json  (backupRoot + devices[])
         │  startup + cron (05:00, 17:00)
         ▼
     server.js  ──►  lib/discovery.js   latest backup per device
         │      ──►  lib/parser.js      FortiGate / PaloAlto / SRX / F5
         │      ──►  lib/scheduler.js   node-cron triggers
         │
         ├──► cache/parsed.json         snapshot; read on restart
         ├──► GET  /api/data            full parsed state → browser
         ├──► GET  /api/status          load status
         ├──► POST /api/reload          manual trigger
         ├──► GET  /api/fqdn?q=…       UltraDNS records (fqdn table)
         └──► GET  /api/local_dns?q=…  on-premise DNS records (local_dns table)
                                               │             │
                                               ▼             ▼
ultradns.py ────────────────►  db/fqdn.db  (fqdn table)
local_dns_csv/*.csv
   └── import_local_dns.py ───►  db/fqdn.db  (local_dns table)

GET /api/data
         │
         ▼
public/index.html  (single-file frontend)
         ├── buildSearchIndex()         once per config load
         ├── getFilteredData()          every search (browser-side)
         └── tabs: Sec Rules / NAT / Routes / Objects / LTM VS / Pools / FQDN / Copy
                                                                           │
                                        Promise.all([/api/fqdn, /api/local_dns])
                                        merged into single results table
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed flow diagrams.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/data` | All parsed configs |
| `GET` | `/api/status` | Load status + device list |
| `POST` | `/api/reload` | Trigger immediate config reload |
| `GET` | `/api/fqdn?q=<keyword>&limit=<n>` | Search UltraDNS records (`fqdn` table) |
| `GET` | `/api/local_dns?q=<keyword>&limit=<n>` | Search on-premise DNS records (`local_dns` table); empty `q` returns `[]` |

---

## FQDN Tab

FQDN records are stored in `db/fqdn.db` (SQLite) in two tables:

| Table | Source | Owner value | Records |
|-------|--------|-------------|---------|
| `fqdn` | UltraDNS cloud DNS (`ultradns.py`) | `ultraDNS` | ~7,880 |
| `local_dns` | On-premise DNS CSV exports (`import_local_dns.py`) | `LocalDNS` | ~6,140 |

Both tables are queried in parallel and their results merged into a single table. The **Owner** column distinguishes the source. The **Owner** dropdown filter lets you restrict to one source.

### Search behaviour

| Search type | How it works |
|-------------|-------------|
| Direct IP / FQDN (e.g. `10.1.2.3`, `mail.example.com`) | Server filters both SQLite tables by keyword; results merged client-side |
| OR-separated FQDNs / IPs (e.g. `taptap.asia OR taptap.zone OR taptap.mobi`) | Each term fetched independently; results unioned. Works in both the global search bar and the local FQDN filter box. |
| Object / group name (e.g. `vs28000_TapTap_MEM`) | All UltraDNS records loaded; client filters by IPs extracted from matching Sec/NAT/LTM results. Local DNS searched by keyword text. |

- The FQDN badge count is pre-loaded in the background after every search — no tab click required.
- The local text filter inside the FQDN tab (FQDN / IP / domain / geo) applies **only when Enter is pressed** and also supports `OR` splitting. Dropdowns (Type, Owner, Geo) still filter immediately on change.

### Single-device filter

When exactly one device is selected in the device bar, the FQDN tab additionally restricts results to records whose IP falls within the **destination** address CIDRs of that device:

- **Firewall (FG / PA / SRX)**: collects address names from `secRules[].destination` and `natRules[].destination`, resolves them recursively through address groups, and converts to `{num, mask}` CIDR pairs.
- **F5 LTM**: uses virtual server IPs directly.

Source-only addresses are excluded. When "All" or multiple devices are selected this filter is not applied.

### Table layout

The FQDN results table uses `table-layout: fixed` with the following column widths:

| Column | Width | Notes |
|--------|-------|-------|
| Owner | 7% | |
| Domain | 13% | |
| FQDN | 28% | |
| Type | 11% | |
| IP | 24% | Increased from 16% (+50%) |
| Geo | 200px (fixed) | `white-space:nowrap; overflow:hidden; text-overflow:ellipsis` via `.fqdn-geo-cell` |
| (actions) | 13% | |

### Result limit

The FQDN tab fetches up to **99,999 records** per source (UltraDNS and Local DNS). Both the frontend request (`limit=99999`) and the backend hard cap (`Math.min(..., 99999)`) enforce this ceiling. The previous limit of 10,000 silently truncated results when the database exceeded that count.

### Syncing FQDN records (`ultradns.py`)

```bash
pip install requests
export ULTRADNS_USERNAME="your-username"
export ULTRADNS_PASSWORD="your-password"
python3 ultradns.py
```

> **Read-only against UltraDNS.** The script issues GET requests only — no DNS records are modified.

Intended for crontab scheduling (e.g. nightly):

```cron
0 3 * * * cd /path/to/NetSearch_claude_sqlite && python3 ultradns.py >> /var/log/ultradns_sync.log 2>&1
```

The script fetches all zones (~1,349) and rrSets concurrently (20 workers), then atomically replaces the `fqdn` table (`DELETE` + `INSERT` in one transaction). Runtime ≈ 68 seconds, ~7,880 records.

---

## Local DNS CSV Sync

On-premise DNS records exported from Windows PowerShell DNS servers are imported into `db/fqdn.db` as a `local_dns` table alongside the UltraDNS `fqdn` table. The FQDN tab queries both in parallel and merges the results.

### CSV folder

Place exported CSV files in `local_dns_csv/` (relative to the project root). Files are discovered dynamically — no hardcoded filenames. Each file is identified by its filename (e.g. `10.11.8.2-DNSRecords.csv`) and re-synced atomically on each run.

### CSV columns

| Column | Imported | Notes |
|--------|----------|-------|
| `ZoneName` | Yes | DNS zone |
| `HostName` | Yes | Record host name |
| `RecordType` | Yes | A, CNAME, MX, etc. |
| `RecordData` | Yes | IP or target value |
| `PSComputerName` | **No** | PowerShell metadata — ignored |
| `RunspaceId` | **No** | PowerShell metadata — ignored |
| `PSShowComputerName` | **No** | PowerShell metadata — ignored |

### SQLite schema (`local_dns` table)

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `source_file` | TEXT | Filename (e.g. `10.11.8.2-DNSRecords.csv`) |
| `zone_name` | TEXT | From `ZoneName` |
| `host_name` | TEXT | From `HostName` |
| `record_type` | TEXT | From `RecordType` |
| `record_data` | TEXT | From `RecordData` |
| `synced_at` | TEXT | ISO8601 UTC timestamp of the sync run |

### Manual sync

```bash
# Sync local DNS CSV files only
python3 import_local_dns.py

# Sync both UltraDNS and local DNS CSV
bash sync_all.sh
```

Example output:

```
=== Local DNS CSV → SQLite sync ===
Found 2 CSV file(s) in local_dns_csv/
  10.11.8.2-DNSRecords.csv | 5004 rows | 0.31s
  10.99.25.2-DNSRecords.csv | 1136 rows | 0.09s
=== Sync complete ===
```

### Crontab example

```cron
0 3 * * * cd /home/local/SSO/yt0115/NetSearch_sqlite && bash sync_all.sh >> /var/log/dns_sync.log 2>&1
```

`sync_all.sh` uses `set -e` — if `ultradns.py` fails, the local DNS sync is skipped.

### API endpoint

```
GET /api/local_dns?q=<keyword>&limit=<n>
```

- Returns `{ results, lastSynced, total }`
- An empty `q` returns `[]` (no full-table dump)
- Searches `zone_name`, `host_name`, and `record_data` fields

Example response:

```json
{
  "results": [
    {
      "id": 142,
      "source_file": "10.11.8.2-DNSRecords.csv",
      "zone_name": "example.local",
      "host_name": "web01",
      "record_type": "A",
      "record_data": "10.11.8.50",
      "synced_at": "2026-05-07T03:00:12.345678+00:00"
    }
  ],
  "lastSynced": "2026-05-07T03:00:12.345678+00:00",
  "total": 1
}
```

---

## Supported Device Types

| Type | Detection | Key sections parsed |
|------|-----------|-------------------|
| FortiGate | `config firewall policy` | Policies, NAT, addresses, groups, routes, schedules, VIPs |
| Palo Alto | `set security policies` | Security rules, NAT rules, address objects, schedules |
| Juniper SRX | `set security zones` | Security policies, SNAT/DNAT rule-sets |
| F5 LTM | `ltm virtual` | Virtual servers, pools, pool members |

---

## Changelog

### 2026-05-07 (2)

**Fix: FQDN tab — OR search now works in the global search bar**

Searching `taptap.asia OR taptap.zone OR taptap.mobi` previously returned no results because the query was treated as an object/group name, which fell into the IP-range filter path and returned `[]` when no rules matched.

- `_fqdnBaseFilter` now detects OR-separated direct keywords and does text matching on `fqdn`/`ip` instead of falling into the IP-range branch
- `fqdnDbAutoLoad` now fetches `/api/local_dns` once per OR term in parallel and unions the results (the API accepts only a single search term)
- The local FQDN filter box (inside the tab) also supports OR splitting since the previous fix

---

### 2026-05-07

**Fix: FQDN result limit increased from 10,000 to 99,999**

The API endpoints `/api/fqdn` and `/api/local_dns` were silently truncating results at 10,000 records. The database now contains 14,020+ FQDN records (7,880 UltraDNS + 6,140 Local DNS), so the old cap hid a significant portion of results.

- `public/index.html` — frontend requests changed from `limit=10000` to `limit=99999`
- `server.js` — backend hard cap changed from `Math.min(..., 10000)` to `Math.min(..., 99999)` for both `/api/fqdn` and `/api/local_dns`

---

## License

MIT
