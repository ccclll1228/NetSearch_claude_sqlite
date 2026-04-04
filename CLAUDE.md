# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
npm install

# Start server (production)
npm start          # node server.js on port 3000

# Start server (dev, auto-restart on file change)
npm run dev        # node --watch server.js
```

There are no tests or lint scripts. The app is accessed at `http://localhost:3000` after starting.

To trigger a manual config reload via API:
```bash
curl -X POST http://localhost:3000/api/reload
curl http://localhost:3000/api/status
```

## Architecture

NetSearch is a network config visualizer for firewall/LTM configs. The architecture separates parsing (server) from search/display (browser).

```
Config files (local paths in config/settings.json)
        ↓  on startup + cron (05:00, 17:00)
server.js          — Express server, in-memory state, API routes
lib/parser.js      — All config parsers (FortiGate, PaloAlto, SRX, F5)
lib/scheduler.js   — node-cron triggers for auto-reload
cache/parsed.json  — JSON snapshot written after each reload; read on restart
        ↓  GET /api/data
public/index.html  — ~3600-line single-file frontend (all CSS + JS inline)
```

**Core principle:** Parse once on the server, serve to all users. All search/filter logic runs in the browser.

### Server (`server.js`)

- Holds in-memory state: `parsedConfigs[]`, `fqdnRecords[]`, `lastLoaded`
- On startup: reads `cache/parsed.json` immediately, then async-parses from disk
- API routes: `GET /api/data`, `GET /api/status`, `POST /api/reload`
- Config paths and cron schedule come from `config/settings.json`

### Parsers (`lib/parser.js`)

Four device parsers, auto-detected by file content:
- **FortiGate** — `config firewall policy` / `config system global`
- **PaloAlto** — `set security policies from-zone` / `set security zones`
- **SRX (Juniper)** — similar `set security` prefix
- **F5** — `ltm virtual` / `ltm pool`

Each parser returns the same shape: `{ type, hostname, addresses{}, groups{}, services{}, serviceGroups{}, secRules[], natRules[], routes[], pools[] }`. Parser functions are also duplicated inline in `public/index.html` for the drag-drop debug flow — **keep both in sync** when changing parsing logic.

### Frontend (`public/index.html`)

Single ~3600-line file. All CSS, JS, and HTML are inline. Key sections in order:
1. **CSS** (~700 lines) — CSS variables at `:root`, component styles
2. **HTML** — header, filter bar, tab bar, modal overlays
3. **JS state** — `state` object (search, filters, active tab, parsed configs)
4. **Network utils** — `ipToNum`, `isCIDR`, `ipInCIDR`, `cidrOverlaps`
5. **Search engine** — `parseSearch` (AST builder), `evaluateAST`, `extractTerms`
6. **Matchers** — `resolveObject` (with WeakMap cache), `_matchNameOnly` (with Map cache), `objectListMatchesSearch`
7. **Config parsers** (duplicated from `lib/parser.js`) — inline versions for drag-drop
8. **Filtering engine** — `getFilteredData()` — runs on every search; builds `allRuleIps`/`allFqdnIps` for symmetric chaining
9. **Renderers** — `renderSecRules`, `renderNatRules`, `renderF5Virtuals`, `renderObjects`, etc.
10. **Event handlers + init** — bottom of file

### Key Performance Notes

- `_resolveObjCache` (WeakMap on `groups` object) caches full group resolution at depth=0
- `_matchNameOnlyCache` (Map, cleared each `getFilteredData()` call) caches recursive group name walks
- `allRuleIps` is capped at 50 entries before symmetric chaining to prevent O(N×M) freeze on large groups
- `esc()` uses string replacement (not `createElement`) for HTML escaping

### Configuration (`config/settings.json`)

```json
{
  "port": 3000,
  "configFiles": [{ "path": "...", "type": "auto" }],
  "fqdnFile": "path/to/fqdn.csv",
  "cronSchedule": ["0 5 * * *", "0 17 * * *"]
}
```

`type` can be `"auto"` (detected from file content) or explicit: `"fortigate"`, `"paloalto"`, `"srx"`, `"f5"`.

### Duplicate Code Warning

`lib/parser.js` and `public/index.html` contain near-identical parser implementations. `lib/parser.js` is the server-side copy; the inline copy in `index.html` is used only for the drag-drop debug flow. If parsing logic changes, update both.
