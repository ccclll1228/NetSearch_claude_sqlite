# NetSearch

A browser-based network configuration search tool for firewall and load-balancer devices.  
Parse and search across FortiGate, Palo Alto, Juniper SRX, and F5 LTM configurations from a single interface.

---

## Features

- Multi-device support: FortiGate, Palo Alto, Juniper SRX, F5 LTM
- Full-text search with boolean operators (`AND`, `OR`, `NOT`)
- Filter by From Zone / To Zone / Tag / Schedule / Source / Destination
- Tabs: Sec Rules, NAT Rules, Routes, Objects, LTM VS, Pools, FQDN, Copy, Raw Config, Debug
- Symmetric chaining — find related rules by shared IPs
- FQDN lookup backed by SQLite (`db/fqdn.db`): UltraDNS cloud records via `ultradns.py` and on-premise DNS via `import_local_dns.py` — both merged in the same results table
- Device Manager — add, edit, and delete server-configured devices from the browser; persists to `config/settings.json` and triggers a live reload without SSH access
- Loading indicator (spinner + "Searching…") flashes on every search trigger across all tabs
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
  "cronSchedule": ["0 5 * * *", "0 17 * * *"]
}
```

| Field | Description |
|-------|-------------|
| `port` | HTTP port (default: 3002) |
| `backupRoot` | Absolute path to the Oxidized backup root directory |
| `devices[].name` | Device name — also used as the filename prefix to locate the latest backup |
| `devices[].type` | `"fortigate"`, `"paloalto"`, `"srx"`, `"f5"`, or `"auto"` |
| `cronSchedule` | Cron expressions for auto-reload (two entries = twice daily) |

**Discovery** — on every reload, `lib/discovery.js` scans `{backupRoot}/{SITE}_{YYYYMMDD}/` folders (newest first) and picks the file with the highest `HHMM` timestamp. Folder and file matching is case-insensitive so device names like `LoadTest-FW01` correctly match backup folders named `LOADTEST_20260508` on Linux filesystems. Any path containing `"UCS"` is excluded.

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

Source-only addresses are excluded. When "All" is selected (no devices disabled) this filter is not applied. When **multiple specific devices** are selected, the filter shows the **union** of all selected devices' address ranges.

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

Place exported CSV files in `local_dns_csv/` (relative to the project root). Export filenames use ISO-style timestamps (e.g. `DNS_Export_Auto_2026-05-07T07-32-09-148Z.csv`). On each run, **only the newest file** (last alphabetically) is imported — older files in the same folder are ignored.

### CSV columns

| Column | Imported | Notes |
|--------|----------|-------|
| `Zone` | Yes | DNS zone |
| `HostName` | Yes | Record host name |
| `Type` | Yes | A, CNAME, MX, etc. |
| `Data` | Yes | IP or target value |
| `Server` | **No** | DNS server — read but not stored |
| Any other columns | **No** | Ignored |

### Import filtering

Records are silently dropped at import time — they never reach SQLite:

**Hidden domains** — any FQDN that exactly matches or is a subdomain of:

| Domain |
|--------|
| `trz.prd` |
| `trz.uat` |
| `sso.trz` |
| `in-addr.arpa` |

**Hidden record types** — records whose `Type` field is:

| Type | Reason |
|------|--------|
| `PTR` | Reverse-lookup noise |
| `SOA` | Zone metadata |
| `WINS` | Legacy Windows name service |

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
Cleared old localDNS rows.
  DNS_Export_Auto_2026-05-07T07-47-09-123Z.csv: 5823 rows

Done. Total inserted: 5823
=== Sync complete: 1 succeeded, 0 failed ===
```

If a file fails to parse, the error is logged to stderr, that file's writes are rolled back, and processing continues. The summary line always reflects actual results.

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

### 2026-05-08 (7)

**Removed: Auto URL Import (Today's Backup)**

The hardcoded Auto URL Import card has been removed from the Import modal. It fetched backup configs from a fixed internal URL (`librenms.opsware.xyz`) and was replaced by server-side auto-discovery via `lib/discovery.js` and the Device Manager. Manual drag-drop, config paste, Device Manager tab, and Reload button are unaffected.

Deleted from `public/index.html`: HTML card (`urlImportBtn`, `urlImportStatus`, `urlImportResults`), `BASE_URL` constant, `BACKUP_CONFIGS` array, `fmtDate` helper, `buildFallbackCandidates` function, and `runUrlImport` async function.

---

### 2026-05-08 (6)

**Docs: CLAUDE.md and ARCHITECTURE.md updated for Device Manager**

`CLAUDE.md` updated: `GET/POST /api/settings` added to the server routes list; `deviceTypes` field added to the configuration example and description table; Device Manager feature bullet added to the Features section. `ARCHITECTURE.md` updated: Config-file Data Flow expanded with the two new routes; Frontend Data Flow block added documenting the Device Manager modal structure, `devMgr` state, and `loadDevMgr` → `saveDevMgr` → `loadFromServer` call chain.

---

### 2026-05-08 (5)

**Feature: Device Manager in the Import modal**

A new **Server Config** tab in the Import modal (`📥 Import` button) lets users manage `config/settings.json` device entries directly from the browser without SSH access:

- **backupRoot** — editable text field at the top of the panel
- **Device table** — shows all configured devices with Name / Type / Actions columns; each row supports inline edit (name input + type dropdown) and delete; **＋ Add Device** appends a new editable row
- **Device Types** — managed as chips; types currently assigned to a device cannot be deleted (chip × is greyed out); new types added via text input
- **Save & Reload** — calls `POST /api/settings` to persist changes then `POST /api/reload` to apply them; status cycles `Saving… → Reloading… → Done. N device(s) loaded.`

Backend: `GET /api/settings` returns `{ backupRoot, devices, deviceTypes }` from `settings.json`; `POST /api/settings` validates and merges the three fields (preserving `port`, `cronSchedule`, etc.) then writes back atomically. A new `"deviceTypes"` array is added to `settings.example.json` (default: `["paloalto", "f5", "fortigate", "srx"]`). Fully bilingual (EN / 中文).

---

### 2026-05-08 (4)

**Refactor: remove dead `fqdnFile` CSV-load code**

The `fqdnFile` setting (`/home/oxidized/backups/all_fqdn.csv`) was a pre-SQLite holdover that is no longer used. FQDN data is now served exclusively via `db/fqdn.db` (populated by `ultradns.py` and `import_local_dns.py`).

Removed from `server.js`: `parseFqdnFile` import, `state.fqdnRecords`, the `settings.fqdnFile` file-read block in `loadAllConfigs()`, and `fqdnRecords` from the cache and `/api/data` response. The `fqdnFile` key is also removed from `config/settings.example.json`.

`parseFqdnFile` in `lib/parser.js` and `public/index.html` is retained — it is still used for manual drag-drop config uploads in the UI.

---

### 2026-05-08 (3)

**Fix: `ultradns.py` — store zone-apex NS records**

Removed the `fqdn == zone_clean` guard in `_parse_rrset()` so zone-apex NS records (e.g. `pdns1.ultradns.net.`) are stored in the database alongside delegation NS records. Previously only sub-zone NS rows were kept.

---

### 2026-05-08 (2)

**Feature: Schedule filter for Sec Rules**

A new `SCHEDULE` dropdown in the global filter bar lets users filter Sec Rules by whether a schedule is applied:

- `SCHEDULE (All)` — no filtering (default)
- `Scheduled Only` — shows only rules where `rule.schedule` is set to a real schedule (not `null`, `'always'`, `'none'`, or `'any'`)
- `Unscheduled Only` — shows only rules with no meaningful schedule applied

The filter is always visible in the filter bar and applies only to Sec Rules. It composes with all existing filters (keyword search, FROM ZONE, TO ZONE, TAG, Hide Disabled, Disabled Only). Fully bilingual (EN / 中文). Implemented via a `hasAppliedSchedule(rule)` utility and two guard lines in the sec rules filtering pipeline; NAT Rules and all other tabs are unaffected.

---

### 2026-05-08

**Feature: Search loading indicator**

A spinner + "Searching…" label now appears above the results area on every search trigger — Enter key, filter dropdown changes, tab switches, search mode toggle, and FQDN async fetches. On synchronous tabs the indicator flashes for at least one visible frame using a double `requestAnimationFrame` hide, so users always get confirmation that a search was triggered regardless of render speed.

Implementation details:
- `<div id="search-loading">` inserted as a static sibling between the tab bar and `#content` — survives `el.innerHTML` replacement on sync renders
- Pure CSS spinner reusing the existing `@keyframes spin` animation; styled with `--cds-*` tokens
- `prefers-reduced-motion`: spinner animation disabled, label remains visible
- `showLoading()` / `hideLoading()` wired into `renderContent()` full-render branch only; `expandOnly` calls (pill expand/collapse, device group toggle) are excluded

---

### 2026-05-07 (4)

**Fix: FQDN tab — EXACT search mode now applies strict equality**

In EXACT mode, the FQDN tab was still doing substring matching (`includes`) instead of strict equality (`===`), so searching `10.0.0.1` would also return results for `10.0.0.10`, `10.0.0.100`, etc.

Three locations patched in `public/index.html`:

- **`_fqdnBaseFilter` — direct keyword path**: added an `isExact` branch that filters rows to strict equality on `fqdn` or `ip` when `state.searchMode === 'exact'`
- **`_fqdnBaseFilter` — OR-of-directs path**: the per-term text match now uses `===` instead of `includes` in EXACT mode
- **`fqdnDbFiltered` — local text filter box**: per-term match switches to strict equality on `fqdn` and `ip` only in EXACT mode (domain and geo fields are excluded from EXACT matching)

KEYWORD mode is unchanged.

---

### 2026-05-07 (3)

**`import_local_dns.py` — multiple improvements**

- **Newest-only import**: only the last file alphabetically in `local_dns_csv/` is imported per run, preventing duplicates from multiple timestamped exports
- **CSV column names updated**: `ZoneName→Zone`, `RecordType→Type`, `RecordData→Data`, `PSComputerName→Server`
- **Import-time filtering**: records are dropped before insert for hidden domains (`trz.prd`, `trz.uat`, `sso.trz`, `in-addr.arpa`) and hidden types (`PTR`, `SOA`, `WINS`)
- **Error resilience**: each file is wrapped in try/except; failures log to stderr and rollback without stopping remaining files; summary line printed at end (`N succeeded, N failed`)
- **Per-file transactions**: each file is committed immediately on success; a failed file is rolled back without affecting already-committed files

**Fix: FQDN tab — multi-device selection shows union of selected devices**

Previously, selecting 2+ specific devices caused the device CIDR filter to return `[]` (the builder had a `configs.length !== 1` guard). Now iterates over all active devices and accumulates a union of their destination CIDRs.

---

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
