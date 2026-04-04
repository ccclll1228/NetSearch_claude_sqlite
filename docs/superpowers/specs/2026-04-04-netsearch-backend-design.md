# NetSearch Backend Design
**Date:** 2026-04-04  
**Status:** Approved

---

## Problem Statement

NetSearch is currently a single-file frontend (`NetSearch-prototype.html`). This causes three critical issues:

1. **Performance** — Large configs (10+ firewalls) parsed in the browser take 10+ seconds per user, per session
2. **Data loss** — F5 / page refresh wipes all loaded data; users must re-import every time
3. **Manual import** — Each user must drag-drop config files themselves; no shared source of truth

Config files are backed up twice daily (05:00 and 17:00). Users always query the latest version.

---

## Users & Environment

- **Users:** Multiple (NetOps team), querying simultaneously
- **Scale:** Large (10+ firewalls, configs potentially 100 MB+, thousands of rules)
- **Deployment:** On-premise internal network (preferred), individual machine (fallback)
- **Config source:** Currently local path (B); future shared NAS/SMB path (A)
- **Update cadence:** Automatic cron at 05:00 and 17:00 daily

---

## Architecture

```
Config files (local / future NAS)
        ↓  cron 05:00 / 17:00
┌──────────────────────────────────┐
│  Node.js + Express Server        │
│                                  │
│  lib/parser.js    ← extracted    │
│    parsePA / parseFortigate /    │
│    parseSRX / parseF5            │
│                                  │
│  lib/scheduler.js ← node-cron   │
│    triggers reload at 05:00/17:00│
│                                  │
│  in-memory state                 │
│    parsedConfigs[]               │
│    fqdnRecords[]                 │
│    lastLoaded: timestamp         │
│                                  │
│  cache/parsed.json (optional)    │
│    written after each reload     │
│    read on server restart        │
│                                  │
│  REST API                        │
│    GET  /api/data                │
│    GET  /api/status              │
│    POST /api/reload              │
│                                  │
│  Static: public/index.html       │
└──────────────────────────────────┘
        ↓  fetch('/api/data') on load
┌──────────────────────────────────┐
│  Browser (NetSearch)             │
│  - No file drag-drop on startup  │
│  - F5 → re-fetches server data   │
│  - Search/filter in browser      │
│  - Status bar: last updated time │
│  - Manual reload button          │
│  - File drag-drop kept for debug │
└──────────────────────────────────┘
```

**Core principle:** Parse once on server, serve to all users. Search/filter logic stays in browser (already optimized with memoization and name-only fast path).

---

## File Structure

```
NetSearch/
├── server.js               # Express entry point, API routes, startup load
├── package.json
├── config/
│   └── settings.json       # Config file paths, port, cron schedule
├── lib/
│   ├── parser.js           # Parsing functions moved from HTML (no logic changes)
│   └── scheduler.js        # node-cron setup
├── public/
│   └── index.html          # Modified frontend (fetch API instead of file input)
└── cache/
    └── parsed.json         # Optional: persisted parsed data for fast restart
```

---

## Configuration

`config/settings.json`:
```json
{
  "port": 3000,
  "configFiles": [
    { "path": "C:/backups/FRI-FW01.conf", "type": "paloalto" },
    { "path": "C:/backups/FRI-FW02.conf", "type": "fortigate" },
    { "path": "C:/backups/F5-LTM.conf",   "type": "f5" }
  ],
  "fqdnFile": "C:/backups/fqdn.csv",
  "cronSchedule": ["0 5 * * *", "0 17 * * *"]
}
```

Future NAS support: change paths to UNC format (`\\\\NAS\\backups\\FW01.conf`). No code changes needed.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/data` | Full parsed state: `{ parsedConfigs, fqdnRecords, lastLoaded }` |
| `GET` | `/api/status` | `{ lastLoaded, loading, devices: [{hostname, ruleCount}] }` |
| `POST` | `/api/reload` | Trigger manual re-parse from disk |

---

## Frontend Changes

**Minimal changes to `public/index.html`:**

1. **On startup:** `fetch('/api/data')` → populate `state.parsedConfigs` and `state.fqdnRecords` (replaces file drag-drop flow)
2. **Status bar:** Add `資料版本：2026-04-04 05:00` label + `🔄 重載` button (calls `POST /api/reload` then re-fetches)
3. **Loading state:** Show spinner while fetching; disable search until data is ready
4. **Keep drag-drop:** Retain existing file drag-drop for local/debug use — hidden by default, accessible via settings or URL param

---

## Parser Migration

Existing parsing functions in the HTML (`parsePA`, `parseFortigate`, `parseSRX`, `parseF5`, `parseFqdn`) are pure JavaScript with no browser API dependencies. Migration steps:

1. Extract functions verbatim to `lib/parser.js`
2. Add `module.exports = { parsePA, parseFortigate, parseSRX, parseF5, parseFqdn }`
3. Remove corresponding code from `public/index.html` (replaced by API fetch)

No logic changes to parsing functions. Identical output to current behavior.

---

## Cron & Reload Flow

```
Server start
  → read cache/parsed.json (if exists) → populate in-memory state
  → then async: parse from disk → update state + overwrite cache

Cron trigger (05:00 / 17:00)
  → parse all configFiles from disk
  → on success: replace in-memory state, write cache/parsed.json, update lastLoaded
  → on error: keep previous state, log error, do not update lastLoaded

POST /api/reload
  → same as cron trigger
  → returns { ok: true, lastLoaded } or { ok: false, error }
```

---

## Dependencies

```json
{
  "express": "^4.18",
  "node-cron": "^3.0",
  "cors": "^2.8"
}
```

No database. No build tools. Node.js standard library for file I/O.

---

## Phased Implementation Plan

### Phase 1 — Core Backend (Priority)
- `server.js` + `lib/parser.js`
- `GET /api/data` working
- Frontend fetches on load; F5 no longer clears data
- **Solves:** data loss, per-user re-import

### Phase 2 — Auto Scheduling
- `lib/scheduler.js` with node-cron
- `GET /api/status` + frontend status bar
- `cache/parsed.json` for restart recovery
- `POST /api/reload` + manual reload button
- **Solves:** manual update, version awareness

### Phase 3 — Network Path & Scale
- UNC/NAS path support (settings only, no code change)
- Load testing with multiple simultaneous users
- Optional: `GET /api/search` server-side search if browser still too slow for very large datasets

---

## Out of Scope

- User authentication / access control (internal network, trusted users)
- Database (in-memory + JSON cache is sufficient for this data size and access pattern)
- Server-side search (browser search with existing optimizations is sufficient for Phase 1–2)
