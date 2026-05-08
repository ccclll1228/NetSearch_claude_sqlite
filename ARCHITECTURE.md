# Architecture

## Directory Structure

```
NetSearch_claude_sqlite/
├── server.js               Express server — in-memory state, API routes
├── ultradns.py             UltraDNS → SQLite sync (standalone, crontab-ready)
├── import_local_dns.py     On-premise DNS CSV → SQLite sync
├── sync_all.sh             Runs ultradns.py then import_local_dns.py (set -e)
├── lib/
│   ├── discovery.js        Resolves latest backup file per device
│   ├── parser.js           Config parsers: FortiGate / PaloAlto / SRX / F5
│   ├── scheduler.js        node-cron auto-reload triggers
│   └── fqdn_db.js          SQLite helper: search/searchLocalDns + getLastSynced
├── public/
│   └── index.html          Single-file frontend (~6,200 lines: CSS + JS + HTML)
├── db/
│   └── fqdn.db             SQLite — fqdn table (UltraDNS + LocalDNS rows)
├── local_dns_csv/          Drop timestamped CSV exports here (gitignored)
├── config/
│   ├── settings.json       Local config (gitignored)
│   └── settings.example.json
└── cache/
    └── parsed.json         Parse cache written after each reload (gitignored)
```

---

## Config-file Data Flow

```
config/settings.json
  backupRoot + devices[]
        │
        │  on startup + cron (05:00, 17:00)
        ▼
  server.js
        ├──► lib/discovery.js
        │      Scan {backupRoot}/{SITE}_{YYYYMMDD}/ folders, newest first.
        │      Folder regex uses 'i' flag; file startsWith uses .toLowerCase()
        │      for case-insensitive matching on Linux filesystems.
        │      Pick the file with the highest HHMM timestamp.
        │      Exclude paths containing "UCS".
        │      Return [{path, type}] — one entry per device.
        │
        ├──► lib/parser.js
        │      parseConfig(text, type) → normalized object:
        │        { type, hostname, addresses{}, groups{},
        │          services{}, serviceGroups{},
        │          secRules[], natRules[], routes[],
        │          virtuals[], pools[] }
        │
        ├──► lib/scheduler.js
        │      node-cron: re-runs loadAllConfigs() at each cron tick.
        │
        ├──► cache/parsed.json
        │      Written after every successful reload.
        │      Read on startup for instant first response while
        │      the async parse runs in the background.
        │
        ├──► GET  /api/data       → full parsedConfigs[] + metadata
        ├──► GET  /api/status     → lastLoaded, device list, error state
        ├──► POST /api/reload     → manual trigger for loadAllConfigs()
        ├──► GET  /api/fqdn       → delegates to lib/fqdn_db.js search()
        ├──► GET  /api/local_dns  → delegates to lib/fqdn_db.js searchLocalDns()
        │                           both cap results at Math.min(limit, 99999)
        ├──► GET  /api/settings   → { backupRoot, devices, deviceTypes } from settings.json
        └──► POST /api/settings   → validate + merge { backupRoot, devices, deviceTypes }
                                    into settings.json (preserves port, cronSchedule, etc.)
```

---

## FQDN Data Flow

```
UltraDNS API  (read-only, GET only)
        │
        │  ULTRADNS_USERNAME / ULTRADNS_PASSWORD (env vars)
        ▼
ultradns.py
        │
        ├── POST /authorization/token → Bearer token
        │
        ├── GET  /v3/zones?limit=1000
        │     cursor-based pagination → ~1,349 zone names
        │
        ├── GET  /zones/{zone}/rrsets?limit=500
        │     asyncio + ThreadPoolExecutor (20 workers)
        │     offset-based pagination per zone
        │
        ├── _parse_rrset()
        │     Profile (geo/IP-pool) records → one row per rdataInfo
        │     Standard A/CNAME/MX/TXT/SPF/APEXALIAS records
        │     NS / SOA silently skipped; unknown types logged + skipped
        │
        └── db/fqdn.db  (fqdn table)
              BEGIN
                DELETE FROM fqdn          ← atomic full replacement
                INSERT all rows           ← synced_at = UTC ISO8601
              COMMIT  (ROLLBACK on error)
              owner = "ultraDNS" · ~7,880 records · runtime ≈ 68 s

local_dns_csv/DNS_Export_Auto_<timestamp>.csv   ← newest file only
        │
        ▼
import_local_dns.py
        │
        ├── Select newest *.csv (alphabetical sort → last entry)
        │
        ├── Filter at import time:
        │     Hidden domains: trz.prd, trz.uat, sso.trz, in-addr.arpa
        │     Hidden types:   PTR, SOA, WINS
        │
        ├── DELETE FROM fqdn WHERE owner = 'localDNS'  ← full replace
        │
        └── db/fqdn.db  (fqdn table)
              Per-file: INSERT rows → COMMIT
                        on error:  ROLLBACK + continue
              owner = "localDNS" · ~5,800+ records

db/fqdn.db  (fqdn table — both sources)
        │
        ▼
server.js  →  lib/fqdn_db.js
        │      search(keyword, limit)       → /api/fqdn
        │      searchLocalDns(keyword, limit) → /api/local_dns
        │      getLastSynced()
        │
        ├── GET /api/fqdn?q=<keyword>&limit=<n>
        └── GET /api/local_dns?q=<keyword>&limit=<n>
                        │               │
                        └───────┬───────┘
                                ▼
                    Promise.all([...]) in fqdnDbAutoLoad()
                    local DNS rows normalised via _normalizeLocalDnsRow()
                      (owner='LocalDNS', fqdn=host.zone, ip=record_data)
                    results merged → fqdnDb.results
                                ▼
                    public/index.html  — FQDN tab
```

---

## Frontend Data Flow

```
GET /api/data  (one fetch per page load or reload)
        │
        ▼
public/index.html  (all logic runs in the browser)
        │
        ├── buildSearchIndex()
        │     Built once after each config load.
        │     cidrList[], ipToObjects Map, nameToRules Map,
        │     memberToParents Map, fqdnMap Map
        │
        ├── getFilteredData()   ← runs on every search / filter change
        │     parseSearch() → AST → evaluateAST()
        │     resolveObject()  (WeakMap cache for group expansion)
        │     Builds allRuleIps (capped 50) for route/addr/f5 chaining
        │     Builds fqdnRuleIpRanges (uncapped) for FQDN IP-range filter
        │     Builds fqdnDeviceCidrRanges for all active devices (union)
        │       (destination addrs from secRules+natRules per device,
        │        recursively resolved through groups; F5: virtual server IPs)
        │     Sec Rules guard chain (in order):
        │       secHideDisabled / secShowDisabledOnly
        │       fromZone / toZone / tag
        │       scheduleFilter → hasAppliedSchedule(rule)
        │         '' = pass all · 'scheduled' = keep matching · 'unscheduled' = keep non-matching
        │       keyword AST match
        │
        └── renderContent(expandOnly)
              │   full render (!expandOnly): showLoading() → el.innerHTML → hideLoading()
              │   expandOnly (pill/group toggle): skips showLoading/hideLoading
              │
              ├── Sec Rules    renderSecRules()
              │                FROM/TO cells → renderZonePills() (static, no expand)
              │                all other cells → renderPills() (expandable)
              ├── NAT Rules    renderNatRules()
              │                FROM/TO cells → renderZonePills() (static, no expand)
              │                all other cells → renderPills() (expandable)
              ├── Routes       renderRoutes()
              ├── Objects      renderObjects()
              ├── LTM VS       renderF5Virtuals()
              ├── Pools        renderF5Pools()
              ├── FQDN         renderFqdnDb() + fqdnDbAutoLoad()
              ├── Copy         renderCopyTab()
              └── Raw Config   renderRawConfig()

Loading indicator:
  #search-loading  ← static sibling between #tabBar and #content (never
                     inside #content, so survives el.innerHTML replacement)
  showLoading()    ← sets display:flex at top of full-render branch
  hideLoading()    ← double requestAnimationFrame; guarantees ≥1 painted
                     frame even on synchronous renders

Device Manager (Import modal — Server Config tab):
  #importModal .modal-body
    ├── .devmgr-tabs tab bar  (Import | Server Config)
    ├── #importTabImport      existing drag-drop content, unchanged
    └── #importTabServerConfig
          rendered entirely by renderDevMgr()
          devMgr = { backupRoot, devices, deviceTypes, editingIdx }
            ← local state, isolated from global state
          loadDevMgr()    → GET /api/settings → populates devMgr
          saveDevMgr()    → POST /api/settings
                          → POST /api/reload
                          → loadFromServer() → renderContent()
          editingIdx = -1  no row in edit mode
          editingIdx = N   row N shows name input + type <select>
          type chip ×      disabled when type is used by any device
```

---

## FQDN Tab — Search Logic

```
state.appliedSearch  (global search bar)
        │
        ▼
_isFqdnDirectKeyword(keyword)?
        │
   yes (IP / CIDR / single domain token)
        │         OR-list of direct keywords        no (object/group name)
        │         e.g. "a.com OR b.com OR c.com"          │
        ▼                    ▼                             ▼
GET /api/fqdn?q=kw    GET /api/fqdn?q=kw (per term, unioned)
GET /api/local_dns    GET /api/local_dns  (per term, unioned)
  (parallel)            (parallel per OR term)         GET /api/fqdn (all)
        │                    │                         GET /api/local_dns?q=kw
        │                    │                             │
        └────────────────────┴─────────────────────────►──┘
                                       │
                             fqdnDb.results  (merged UltraDNS + LocalDNS)
                                       │
                                       ▼
                             _fqdnBaseFilter(rows)
                             1. keyword routing:
                                • direct keyword  → pass through (server-filtered)
                                                    EXACT mode: strict === on fqdn/ip
                                • OR-of-directs   → text OR match on fqdn/ip
                                                    EXACT mode: === per term
                                • object/group    → IP-range filter (fqdnRuleIpRanges)
                                                    returns [] if no rules matched
                             2. device CIDR filter (fqdnDeviceCidrRanges)
                                union of all active devices' destination CIDRs
                                skipped when all devices are active (size=0)
                                       │
                                       ▼
                             fqdnDbFiltered()  ← base filter + local text/dropdowns
                             local text box supports OR splitting on Enter
                             EXACT mode: === on fqdn/ip only (domain/geo excluded)
                                       │
                                       ▼
                             Table rows + badge count

Background pre-load:
  After every renderContent() (any tab), fqdnDbAutoLoad(true) is called
  via setTimeout so the FQDN badge is always up-to-date without a tab switch.
  Badge = _fqdnBaseFilter(fqdnDb.results).length (keyword + device filters,
  no local text/dropdown filters). Re-renders only when count changes.

Local text filter (inside FQDN tab):
  Updates fqdnDb.query on Enter only (no keystroke filtering).
  Supports OR splitting: "foo OR bar" matches rows containing either term.
  Dropdowns (Type / Owner / Geo) still apply immediately on change.
```

## FQDN Tab — Table Column Layout

```
table-layout: fixed  (enforces column widths regardless of content)

Col   Selector / class     Width       Notes
────  ──────────────────   ─────────   ────────────────────────────────
Owner                      7%
Domain                     13%
FQDN                       28%
Type                       11%
IP                         24%         Increased from 16% (+50%)
Geo   .fqdn-geo-cell       200px       white-space:nowrap; overflow:hidden;
                           (fixed)     text-overflow:ellipsis on both
                                       <th> and <td>
      (actions)            13%
```

---

## UltraDNS Sync Pipeline (detailed)

```
┌─────────────────────────────────────────────────────────────────┐
│  Environment                                                    │
│  ULTRADNS_USERNAME / ULTRADNS_PASSWORD                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Authentication                                                 │
│  POST https://api.ultradns.com/authorization/token              │
│  grant_type=password  →  accessToken (Bearer)                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Zone List   GET /v3/zones?limit=1000                           │
│                                                                 │
│  Page 1 ──► cursorInfo.next ──► Page 2 ──► no next ──► stop    │
│  • Skip zones containing "sanbox"                               │
│  • Strip trailing dot from zone names                           │
│  • Result: ~1,349 zone names                                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  rrSets Fetch   GET /zones/{zone}/rrsets?limit=500              │
│                                                                 │
│  asyncio + ThreadPoolExecutor (20 workers)                      │
│  Per zone: offset=0 → paginate until returnedCount < totalCount │
│  On error per zone: log + continue (no abort)                   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Record Parsing   _parse_rrset()                                │
│                                                                 │
│  Profile records (geo/IP-pool)                                  │
│    profile present AND no ttl at rrset level                    │
│    → one row per rdataInfo (ttl, type, geo_info from entry)     │
│                                                                 │
│  Standard records                                               │
│    (1)   A          → rdata joined ","                          │
│    (5)   CNAME      → rdata joined ","                          │
│    (15)  MX         → rdata joined ","                          │
│    (16)  TXT        → rdata joined ",", skip if > 255 chars     │
│    (99)  SPF        → same as TXT                               │
│    (65282) APEXALIAS → same as CNAME                            │
│    (2)   NS         → all rows stored (zone-apex + sub-zone)    │
│    (28)  AAAA       → logged [unhandled], skipped               │
│    (33)  SRV        → logged [unhandled], skipped               │
│    (6)   SOA        → silently skipped                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  SQLite Write   db/fqdn.db                                      │
│                                                                 │
│  BEGIN                                                          │
│    DELETE FROM fqdn          ← atomic full replacement          │
│    INSERT all records        ← synced_at = UTC ISO8601          │
│  COMMIT   (ROLLBACK on error)                                   │
│                                                                 │
│  Columns: fqdn, ip, owner ("ultraDNS"), domain, type,           │
│           ttl, geo_info, synced_at                              │
│  Indexes: idx_fqdn, idx_ip, idx_geo                             │
└─────────────────────────────────────────────────────────────────┘
```
