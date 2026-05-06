# Architecture — UltraDNS Sync Pipeline

## Sync pipeline (`ultradns.py`)

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
│  grant_type=password                                            │
│  → accessToken (Bearer)                                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Zone List   GET /v3/zones?limit=1000                           │
│                                                                 │
│  Page 1 ──► cursorInfo.next ──► Page 2 ──► no next ──► stop    │
│                                                                 │
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
│                                                                 │
│  Per zone:                                                      │
│    offset=0 ──► returnedCount < totalCount? ──► offset+=N ──┐  │
│    └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  On error per zone: print + continue (no abort)                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Record Parsing   _parse_rrset()                                │
│                                                                 │
│  Profile records (geo/IP-pool)                                  │
│    profile present AND no ttl at rrset level                    │
│    → one row per rdataInfo entry                                │
│    → ttl, type, geo_info from rdataInfo                         │
│                                                                 │
│  Standard records                                               │
│    (1)  A         → rdata joined ","                            │
│    (5)  CNAME     → rdata joined ","                            │
│    (15) MX        → rdata joined ","                            │
│    (16) TXT       → rdata joined ",", skip if > 255 chars       │
│    (99) SPF       → same as TXT                                 │
│    (65282) APEXALIAS → same as CNAME                            │
│    (2)  NS        → silently skipped                            │
│    (6)  SOA       → silently skipped                            │
│    other          → logged as [unhandled], skipped              │
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

## NetSearch server + frontend

```
config/settings.json
  backupRoot + devices[]
        │  on startup + cron (05:00, 17:00)
        ▼
  server.js  ──►  lib/discovery.js   resolve latest backup per device
        │    ──►  lib/parser.js      parse FortiGate / PaloAlto / SRX / F5
        │    ──►  lib/scheduler.js   node-cron triggers
        │
        ├──► cache/parsed.json       snapshot written after each reload
        │        └── read on restart (fast cold start)
        │
        ├──► GET  /api/data          full parsed state → browser
        ├──► GET  /api/status        load status + device list
        ├──► POST /api/reload        manual reload trigger
        └──► GET  /api/fqdn?q=...   SQLite FQDN search via lib/fqdn_db.js
                                            │
                                            ▼
                                     db/fqdn.db  (written by ultradns.py)

  GET /api/data
        │
        ▼
  public/index.html  (single-file: ~6,200 lines, CSS + JS + HTML inline)
        │
        ├── buildSearchIndex()       built once per config load
        ├── getFilteredData()        runs on every keystroke (browser-side)
        ├── renderContent()          tab renderer — sec/nat/route/objects/f5/fqdn
        └── renderFqdnDb()          FQDN tab — fetches /api/fqdn on input ≥ 2 chars
```
