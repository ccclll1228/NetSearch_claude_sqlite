# Architecture

## Directory Structure

```
NetSearch_claude_sqlite/
├── server.js          Express server — in-memory state, API routes
├── ultradns.py        UltraDNS → SQLite sync (standalone, crontab-ready)
├── lib/
│   ├── discovery.js   Resolves latest backup file per device
│   ├── parser.js      Config parsers: FortiGate / PaloAlto / SRX / F5
│   ├── scheduler.js   node-cron auto-reload triggers
│   └── fqdn_db.js     SQLite helper: search() + getLastSynced()
├── public/
│   └── index.html     Single-file frontend (~6,200 lines: CSS + JS + HTML)
├── db/
│   └── fqdn.db        SQLite — FQDN records written by ultradns.py
├── config/
│   ├── settings.json  Local config (gitignored)
│   └── settings.example.json
└── cache/
    └── parsed.json    Parse cache written after each reload (gitignored)
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
        ├──► GET  /api/data     → full parsedConfigs[] + metadata
        ├──► GET  /api/status   → lastLoaded, device list, error state
        └──► POST /api/reload   → manual trigger for loadAllConfigs()
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
        └── db/fqdn.db  (SQLite)
              BEGIN
                DELETE FROM fqdn          ← atomic full replacement
                INSERT all rows           ← synced_at = UTC ISO8601
              COMMIT  (ROLLBACK on error)

              Columns: fqdn, ip, owner ("ultraDNS"), domain,
                       type, ttl, geo_info, synced_at
              Indexes: idx_fqdn, idx_ip, idx_geo
              ~7,880 records · runtime ≈ 68 s

db/fqdn.db
        │
        ▼
server.js  →  lib/fqdn_db.js
        │      search(keyword, limit) — parameterised SQL
        │      getLastSynced()
        ▼
GET /api/fqdn?q=<keyword>&limit=<n>
        │
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
        │
        └── renderContent()
              ├── Sec Rules    renderSecRules()
              ├── NAT Rules    renderNatRules()
              ├── Routes       renderRoutes()
              ├── Objects      renderObjects()
              ├── LTM VS       renderF5Virtuals()
              ├── Pools        renderF5Pools()
              ├── FQDN         renderFqdnDb() + fqdnDbAutoLoad()
              ├── Copy         renderCopyTab()
              └── Raw Config   renderRawConfig()
```

---

## FQDN Tab — Search Logic

```
state.appliedSearch  (global search bar)
        │
        ▼
_isFqdnDirectKeyword(keyword)?
        │
   yes (IP / CIDR / domain with dot, single token)
        │                   no (object/group name, multi-token OR, etc.)
        ▼                           ▼
GET /api/fqdn?q=keyword       GET /api/fqdn  (all records, no filter)
Server filters SQLite          ~7,880 rows loaded into fqdnDb.results
        │                           │
        │                           ▼
        │                   fqdnDbFiltered()
        │                   Filter fqdnDb.results client-side using
        │                   fqdnRuleIpRanges from getFilteredData()
        │                   (IPs extracted from matching Sec/NAT/LTM rules)
        │                           │
        └─────────────────────────►─┘
                                   │
                                   ▼
                        Table rows + badge count

Background pre-load:
  After every renderContent() (any tab), fqdnDbAutoLoad(true) is called
  via setTimeout so the FQDN badge is always up-to-date without a tab switch.
  When data is already loaded (__all__), only the badge count is recomputed
  from the current fqdnRuleIpRanges — no re-fetch.

Local text filter (inside FQDN tab):
  Updates fqdnDb.query on every keystroke but re-renders only on Enter.
  Dropdowns (Type / Owner / Geo) still apply immediately on change.
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
│    (28)  AAAA       → logged [unhandled], skipped               │
│    (33)  SRV        → logged [unhandled], skipped               │
│    (2)   NS         → silently skipped                          │
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
