# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
npm install

# Start server (production)
npm start          # node server.js

# Start server (dev, auto-restart on file change)
npm run dev        # node --watch server.js
```

There are no tests or lint scripts. The port is read from `config/settings.json` (currently `3002`). The app is accessed at `http://localhost:3002` after starting.

To trigger a manual config reload via API:
```bash
curl -X POST http://localhost:3002/api/reload
curl http://localhost:3002/api/status
```

## Architecture

NetSearch is a network config visualizer for firewall/LTM configs. The architecture separates parsing (server) from search/display (browser).

```
config/settings.json (backupRoot + devices[])
        ↓  on startup + cron (05:00, 17:00)
server.js          — Express server, in-memory state, API routes
lib/discovery.js   — Resolves latest backup file per device at load time
lib/parser.js      — All config parsers (FortiGate, PaloAlto, SRX, F5)
lib/scheduler.js   — node-cron triggers for auto-reload
lib/fqdn_db.js     — SQLite helper: search/searchLocalDns + getLastSynced
cache/parsed.json  — JSON snapshot written after each reload; read on restart
        ↓  GET /api/data          GET /api/fqdn     GET /api/local_dns
public/index.html  — ~6200-line single-file frontend (all CSS + JS inline)

db/fqdn.db         — SQLite; fqdn table (UltraDNS + LocalDNS rows)
        ↑  ultradns.py            (owner='ultraDNS', crontab-ready)
        ↑  import_local_dns.py   (owner='localDNS',  reads local_dns_csv/)
        ↑  sync_all.sh            (runs both in sequence, set -e)
```

**Core principle:** Parse once on the server, serve to all users. All search/filter logic runs in the browser.

### Server (`server.js`)

- Holds in-memory state: `parsedConfigs[]`, `lastLoaded`
- On startup: reads `cache/parsed.json` immediately, then async-parses from disk
- API routes: `GET /api/data`, `GET /api/status`, `POST /api/reload`, `GET /api/fqdn`, `GET /api/local_dns`, `GET /api/settings`, `POST /api/settings`
- `/api/fqdn` and `/api/local_dns` delegate to `lib/fqdn_db.js`; both cap results at `Math.min(limit, 99999)`
- Calls `resolveDevicePaths()` at the start of `loadAllConfigs()` to get `[{path, type}]` from discovery; cron schedule comes from `config/settings.json`

### Discovery (`lib/discovery.js`)

- `resolveDevicePaths(devices, backupRoot)` — scans `{SITE}_{YYYYMMDD}` folders, newest first
- Site prefix derived from device name: `FRI-LTM01` → looks in `FRI_*` folders; folder regex uses `'i'` flag and file `startsWith` uses `.toLowerCase()` on both sides for case-insensitive matching on Linux filesystems (e.g. device `LoadTest-FW01` matches folder `LOADTEST_20260508`)
- Within a folder, picks the file with the highest `HHMM` timestamp (1700 beats 0500); lexicographic tie-break
- Any folder or file containing `"UCS"` is excluded
- Returns `[{path, type}]` — same shape the existing `loadAllConfigs()` loop consumes
- Skips devices with no match (logs a `[discovery]` warning); never throws

### Parsers (`lib/parser.js`)

Four device parsers, auto-detected by file content:
- **FortiGate** — `config firewall policy` / `config system global`
- **PaloAlto** — `set security policies from-zone` / `set security zones`
- **SRX (Juniper)** — similar `set security` prefix
- **F5** — `ltm virtual` / `ltm pool`

Each parser returns the same shape: `{ type, hostname, addresses{}, groups{}, services{}, serviceGroups{}, secRules[], natRules[], routes[], pools[] }`. Parser functions are also duplicated inline in `public/index.html` for the drag-drop debug flow — **keep both in sync** when changing parsing logic.

### Frontend (`public/index.html`)

Single ~6200-line file. All CSS, JS, and HTML are inline. Key sections in order:
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

### Search Index (`buildSearchIndex`)

Built once after each config load; stored at `state.searchIndex`. Reduces IP search from O(rules×objects) to O(candidates).

Structure:
- `cidrList[]` — all address objects with CIDR/IP values, for range matching
- `ipToObjects` — `Map<ip, [{objectName, device}]>` — exact IP → address objects
- `nameToRules` — `Map<"device|objectName", Set<rule>>` — object name → rules that reference it directly
- `memberToParents` — `Map<"device|memberKey", Set<"device|groupName">>` — reverse group membership index (leaf → parent groups)
- `fqdnMap` — `Map<ip, [{fqdn,...}]>` — FQDN lookup

When a search term is an IP, `resolveIndexCandidates()` walks the index upward (leaf → parent groups → rules) instead of scanning all rules. Non-IP searches fall back to full `getFilteredData()` scan.

### Key Performance Notes

- `_resolveObjCache` (WeakMap on `groups` object) caches full group resolution at depth=0
- `_matchNameOnlyCache` (Map, cleared each `getFilteredData()` call) caches recursive group name walks
- `allRuleIps` is capped at 50 entries for routes/addresses/f5 chaining to prevent O(N×M) freeze on large groups
- `allRuleIpsForFqdn` is uncapped — CIDRs pre-converted to `{num,mask}` pairs for fast bitwise IP matching in FQDN tab
- `esc()` uses string replacement (not `createElement`) for HTML escaping
- Pill expand/collapse uses targeted DOM patching — never calls `renderContent()` for expand/collapse actions:
  - `_patchPillsChunked()` — rAF batches of 30 pills for Tab Expand/Collapse All (sec/nat)
  - `_patchPidsDirect(pids)` — synchronous patch for single rule card expand/collapse
  - `_findRootPid(pid)` — strips `__suffix` to locate top-level `_pillContext` entry for nested node toggle
  - `_patchGeneration` counter — cancels stale rAF loops when a new render/patch starts
- `_pillContext` Map (pid → `{item, type, parsed, ctx}`) and `_ruleExpandMap` (ruleKey → `{hostname, items, ctx}`) are populated during `renderPills()` and required by all DOM patch functions
- `renderZonePills(list)` — static variant used **only** for FROM/TO zone columns in Sec Rules and NAT Rules. Emits plain `<span class="pill">` with no `data-ppid`, no onclick, no QS/copy buttons, and no `_pillContext` registration. Zone items still appear in `expandableItems` but `_patchPidsDirect` silently skips them (`if (!pctx) continue`). Do not use `renderPills` for FROM/TO zones.

### CSS Token System

All CSS variables use `--cds-*` (Carbon Design System) tokens. Key mapping from legacy names:

| Legacy | `--cds-*` token | Value |
|--------|----------------|-------|
| `--bg` | `--cds-background` | `#f4f4f4` |
| `--bg-card` | `--cds-layer-01` | `#ffffff` |
| `--bg-hover` | `--cds-layer-hover` | `#e8e8e8` |
| `--bg-elevated` | `--cds-layer-02` | `#e0e0e0` |
| `--border` | `--cds-border-subtle` | `#c6c6c6` |
| `--border-focus` | `--cds-focus` | `#0f62fe` |
| `--text` | `--cds-text-primary` | `#161616` |
| `--text-secondary` | `--cds-text-secondary` | `#525252` |
| `--text-muted` | `--cds-text-placeholder` | `#6f6f6f` |
| `--accent` | `--cds-interactive` | `#0f62fe` |
| `--accent-light` | `--cds-highlight` | `#edf5ff` |
| `--accent-hover` | `--cds-interactive-hover` | `#0353e9` |
| `--accent-glow` | — | `transparent` |
| `--green` | `--cds-support-success` | `#24a148` |
| `--red` | `--cds-support-error` | `#da1e28` |
| `--yellow` | `--cds-support-warning` | `#f1c21b` |
| `--orange` | `--cds-support-caution` | `#ff832b` |
| `--blue` | `--cds-link-primary` | `#0f62fe` |
| `--pill-bg` | `--cds-background` | `#f4f4f4` |
| `--pill-match` | `--cds-highlight` | `#edf5ff` |
| `--radius` | `--cds-radius` | `0px` |
| `--radius-sm` | `--cds-radius` | `0px` |
| `--font-ui` | `--cds-font-sans` | IBM Plex Sans |
| `--font-mono` | `--cds-font-mono` | IBM Plex Mono |

Do not introduce new ad-hoc CSS variables; always use `--cds-*` tokens.

### Configuration (`config/settings.json`)

```json
{
  "port": 3002,
  "backupRoot": "/home/oxidized/backups",
  "devices": [
    { "name": "FRI-LTM01", "type": "f5" },
    { "name": "FRI-FW01",  "type": "fortigate" }
  ],
  "deviceTypes": ["paloalto", "f5", "fortigate", "srx"],
  "cronSchedule": ["0 5 * * *", "0 17 * * *"]
}
```

- `backupRoot` — absolute path to the Oxidized backup root; discovery scans `{SITE}_{YYYYMMDD}` subfolders
- `devices[].name` — device identifier and filename prefix (e.g. `FRI-LTM01` matches `FRI-LTM01_*.txt`)
- `devices[].type` — passed through to the parser: `"f5"`, `"fortigate"`, `"paloalto"`, `"srx"`, `"auto"`
- `deviceTypes` — list of allowed device type strings shown in the Device Manager dropdown; defaults to `["paloalto", "f5", "fortigate", "srx"]` if absent; editable from the UI via `POST /api/settings`
- `configFiles` — **removed**; replaced by `backupRoot + devices[]`
- `fqdnFile` — **removed**; FQDN data is served exclusively via `db/fqdn.db` (`ultradns.py` + `import_local_dns.py`)

`config/settings.json` is gitignored. Use `config/settings.example.json` as the template.

> **Note:** `README.md` is outdated — it still documents the old `configFiles` schema. Do not follow it for configuration; use this file instead.

### Features

- **UltraDNS `_parse_rrset` record types** — `ultradns.py` stores: A, CNAME, MX, TXT (≤255 chars), SPF (≤255 chars), APEXALIAS, NS (all rows — both zone-apex and sub-zone delegations). SOA is silently skipped; AAAA/SRV are logged as unhandled and skipped. Profile (geo/IP-pool) records produce one row per `rdataInfo` entry.
- **Local DNS CSV sync** (`import_local_dns.py`) — imports on-premise DNS records from `local_dns_csv/*.csv` into the `fqdn` table (`owner='localDNS'`). Scans for the newest CSV only (alphabetical sort). Hidden domains (`trz.prd`, `trz.uat`, `sso.trz`, `in-addr.arpa`) and hidden types (`PTR`, `SOA`, `WINS`) are dropped at import time. `sync_all.sh` runs `ultradns.py` then `import_local_dns.py` in sequence. `GET /api/local_dns` searches these rows via `lib/fqdn_db.js`; the FQDN tab fetches both endpoints in parallel and union-merges results.
- **FQDN tab device filter** — when one or more specific devices are selected in the device bar, the FQDN tab only shows records whose IPs fall within the **union** of all selected devices' destination CIDRs (FW: enabled ALLOW rule destinations → address objects + 1-level group expansion; F5: virtual server IPs). `fqdnDeviceCidrRanges` is built with `configs.forEach` over all active devices. Selecting "All" skips the filter entirely.
- **Ignore CIDR toggle** — when enabled, CIDR containment is skipped across all search and filter operations; only exact-IP matches are used. Affects both the search pipeline and the FQDN device filter gate.
- **`_32` notation support** — IP addresses written as `x.x.x.x_32` (Palo Alto style) are normalised to `x.x.x.x/32` at index build time and throughout the search/filter pipeline.
- **Schedule filter for Sec Rules** — `SCHEDULE` dropdown in the global filter bar (`state.filters.scheduleFilter`: `''` | `'scheduled'` | `'unscheduled'`). `hasAppliedSchedule(rule)` utility returns `true` when `rule.schedule` is non-empty and not `'none'`/`'any'`/`'always'`; handles `null`, raw strings, and resolved schedule objects. Two guard lines in the sec rules loop in `getFilteredData()` immediately after the `filters.tag` check. NAT rules loop is untouched. Fully bilingual via `scheduleAll`/`scheduleOnly`/`scheduleNone` i18n keys; `applyLang()` updates option texts on language toggle.
- **Schedule column in Sec Rules** — FortiGate (`config firewall schedule onetime`) and Palo Alto (`set schedule ... schedule-type non-recurring`) schedule objects are parsed into `parsed.schedules[name] = { name, start, end }` (ISO datetime strings). Each `secRule.schedule` is resolved to the object when a match exists, kept as a raw string otherwise, or `null`. `renderSecRules` detects whether any visible rule carries a non-`"always"` schedule; if so it switches to an 8-column grid (`9% 130px 10% 18% 18% 10% 9% auto`) and inserts a SCHEDULE column after RULE/ACTION. The cell shows: schedule name (bold, wrapping), start datetime, end datetime — with a yellow `#fffde7` background when the window end is still in the future. If no rule has a schedule the column is suppressed entirely and the original 7-column grid is preserved. NAT Rules tab is unaffected.
- **VIP/VIPGRP resolution in Sec Rules** — FortiGate `config firewall vip` blocks are parsed into `parsed.vipMap[name] = { extip, mappedip, extintf }`; `config firewall vipgrp` blocks into `parsed.vipgrpMap[name] = { members: [] }`. During secRules serialization, each destination address is passed through `resolveVip()`: vipgrp names expand to their member VIP entries, vip names resolve directly, plain addresses return `null`. When any destination resolves, `secRule.dstVips = [{ name, extip, mappedip }, ...]` is attached. In `renderSecRules`, the DESTINATION cell appends one `extip → mappedip` sub-line per entry (0.75rem, gray, monospace) below the address pills so the real mapped IP is visible without expanding.
- **Objects tab layout** — two-panel CSS grid (Addresses | Address Groups) with a `1px` center divider; `table-layout:fixed` on the addresses table prevents content from overflowing the grid cell; NAME column wraps long names (`word-break:break-all`); TYPE badge is `white-space:nowrap`; alternating row tint (`var(--cds-layer-02)`) for scanability; section headers are `position:sticky` so they remain visible while scrolling.
- **EXACT search mode in FQDN tab** — when `state.searchMode === 'exact'`, `_fqdnBaseFilter` uses `===` instead of `includes` for direct keyword and OR-of-directs matching; `fqdnDbFiltered` local text filter also uses `===` on `fqdn`/`ip` only (domain and geo fields are excluded from EXACT matching). KEYWORD mode is unchanged.
- **Search loading indicator** — `<div id="search-loading">` sits as a static sibling between `#tabBar` and `#content` in the HTML. It is never inside `#content`, so it survives `el.innerHTML` replacement on synchronous renders. `showLoading()` sets its display to `flex`; `hideLoading()` hides it via double `requestAnimationFrame` to guarantee at least one painted frame. Both are called inside `renderContent()`: `showLoading()` at the top of the full-render (`!expandOnly`) branch, `hideLoading()` after the `el.innerHTML` switch. `expandOnly` calls (pill expand/collapse, device group toggle) do not trigger the indicator. The existing `#searchSpinner` in the header is separate and untouched.
- **Filter bar dropdowns** — the Src/Dst, Hide Disabled/Disabled Only, and F5 Disabled controls are `<select class="filter-select">` dropdowns (not checkboxes). IDs: `ipFilter` (options: `""` / `"src"` / `"dst"`), `ruleDisabledFilter` (options: `""` / `"hide"` / `"only"`), `f5DisabledFilter` (options: `""` / `"only"`). Inline `onchange` handlers set the same state variables as before: `filterSource`, `filterDest`, `secHideDisabled`, `natHideDisabled`, `secShowDisabledOnly`, `natShowDisabledOnly`, `showDisabledMembersOnly`. `clearAllFilters()` resets them via `.value = ''`. No `addEventListener` calls exist for these three controls. `.filter-select` uses `font-size: 0.75em` and `padding: 2px 20px 2px 6px` (smaller than default 14px / `0 32px 0 12px`; 20px right clears the 10px-wide SVG chevron anchored at `right 10px`).
- **Device Manager** — Server Config tab in the Import modal (`#importModal`). Tab bar (`Import` | `Server Config`) inserted at top of `modal-body`; existing import content (drag-drop, config paste) unchanged inside `#importTabImport`. The former "Auto URL Import (Today's Backup)" card has been removed — server-side discovery via `lib/discovery.js` supersedes it. `#importTabServerConfig` is rendered entirely by `renderDevMgr()`. Local state object `devMgr = { backupRoot, devices, deviceTypes, editingIdx }` — isolated from global `state`; all edits are local until Save & Reload. `loadDevMgr()` fetches `GET /api/settings` and populates `devMgr`. `saveDevMgr()` posts to `POST /api/settings`, then calls `POST /api/reload` + `loadFromServer()` to refresh the page. One row at a time can be in edit mode (`editingIdx`). Device type chips show `×` disabled (with tooltip) when the type is assigned to any device. `applyLang()` re-renders the panel when the Server Config tab is visible.

### resolveObject() is flatten-only — never reuse for hierarchical output

`resolveObject()` expands all address groups to a **flat leaf list** (no depth metadata).
Use it for search/match scenarios only.

For any output that must preserve tree structure (copy text, tree rendering), write a
dedicated recursive walker that walks `groups[name]` directly, emitting each sub-group
name line **before** recursing into its members. See `tasks/lessons.md` for the pattern.

### Frontend Design System

`DESIGN.md` defines the IBM Carbon-inspired visual language used throughout the UI:
- Single accent: IBM Blue 60 (`#0f62fe`) — buttons, links, focus states
- 0px border-radius on all interactive elements (buttons, inputs, cards)
- IBM Plex Sans (weight 300/400/600 only) + IBM Plex Mono for code/data
- Depth via background-color layering (`#fff` → `#f4f4f4` → `#e0e0e0`), no box-shadows
- Bottom-border inputs only (not boxed); 8px spacing grid throughout

### FQDN Device Filter — Technical Notes

- **`activeDeviceIpFilter`** — built per render inside `getFilteredData()` when `state.disabledHosts.size > 0`. Iterates only the active (non-disabled) `configs`. For FW devices (FortiGate / PA / SRX): collects destination names from enabled ALLOW `secRules`, resolves them through `parsed.addresses` (direct) or `parsed.groups` (one level of indirection, member → `parsed.addresses[member].value`). For F5 devices: collects `parsed.virtuals[].ip`. Result: `{ exactIps: Set<string>, cidrRanges: [{num, mask}] }`.
- **`fqdnDeviceCidrRanges`** — IIFE inside `getFilteredData()` that builds the FQDN device filter. Uses `configs.forEach` to iterate all active devices and accumulate a union of their destination CIDRs into a shared `ranges` array. Each device gets its own `seen` Set and `resolveAddr` closure; `addAddr`/`ranges` are shared across all devices. Returns `[]` when all devices are active (size=0), skipping the filter entirely.
- **`ignoreCIDR` guard** — applied at ~10 locations in the search/filter pipeline; when true the `cidrRanges` loop is skipped and only `exactIps.has(r.ip)` is tested.
- **`/32` special-case in `addValue()`** — `/32` CIDRs are added to `exactIps` only and return early; they are never pushed to `cidrRanges`. Reason: JavaScript's `>>>` operator is mod-32, so `0xFFFFFFFF >>> 32 === 0xFFFFFFFF`, making `~(0xFFFFFFFF >>> 32) >>> 0 === 0`. A `mask=0` entry in `cidrRanges` satisfies `((rn & 0) >>> 0) === 0` for every IP in the universe, bypassing the filter entirely.

### Duplicate Code Warning

`lib/parser.js` and `public/index.html` contain near-identical parser implementations. `lib/parser.js` is the server-side copy; the inline copy in `index.html` is used only for the drag-drop debug flow. If parsing logic changes, update both.

### Search Logic Invariants — Rules That Must Never Be Broken

The following invariants protect the correctness of AND/OR/NOT Boolean search semantics.
Any future modification to the search pipeline must verify all invariants still hold.

#### 1. extractPositiveTerms vs extractTerms
- `termFqdnIpsMap` and `termRuleIpsMap` must be built using `extractPositiveTerms` only
- Terms inside NOT branches must NOT contribute IPs to any chain
- Reason: searching `NOT DENY_NON_SERVICE` must not let that rule's IPs pollute other terms' chain results

#### 2. Per-term FQDN chain (termFqdnIpsMap[term])
- Inside `evaluateAST`'s `matchFn`, each term must only use its own `termFqdnIpsMap[term]` IP set
- Never use `allFqdnIps` (the global union) inside `matchFn`
- Reason: in `AND(term1, term2)`, if term1's FQDN IPs satisfy term2's match condition, AND semantics break

#### 3. allRuleIps size cap (>50 → clear)
- If `allRuleIps.size > 50`, call `allRuleIps.clear()` — do NOT use it for route/address chaining
- Keep `allRuleIpsForFqdn` uncapped — FQDN IP matching uses bitwise ops (cheap)
- Scenario this protects: searching an address group with 243 members causes O(N×M) freeze

#### 4. /32 CIDR must go into exactIps, never cidrRanges
- Any CIDR with prefix length 32 must be added to `exactIps`, not `cidrRanges`
- Reason: JavaScript `>>>` is mod-32, so `0xFFFFFFFF >>> 32 === 0xFFFFFFFF`
  This makes mask=0, which matches every IP — the entire FQDN DB would be displayed

#### 5. ignoreCIDR auto-enable in Exact+IP mode
- If `searchMode === 'exact'` AND `searchAST` contains any IP/CIDR term → force `ignoreCIDR = true`
- This ensures exact mode only does base-IP equality matching, no containment checks

#### 6. resolveObject is flatten-only
- `resolveObject` returns a flat leaf-node list with no depth or parent information
- Features requiring tree structure (copy text, tree view) must write a separate recursive walker
  directly over `groups[name]` — do NOT attempt to reuse `resolveObject` for this

#### 7. renderZonePills vs renderPills
- FROM/TO zone columns must use `renderZonePills` (no `data-ppid`, no `onclick`)
- Using `renderPills` on zone columns will cause `_pillContext` to register zone entries,
  and `_patchPidsDirect` will attempt to patch a pill structure that does not exist


## MCP Tools
- Always use Context7 when referencing any library documentation
- Before writing code using any npm package or framework, use Context7 to fetch up-to-date docs first

## Workflow Orchestration
### 1. Plan Mode Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity
### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One task per subagent for focused execution
### 3. Self-Improvement Loop
- After ANY correction from the user: update tasks/lessons.md with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project
### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness
### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes -- don't over-engineer
- Challenge your own work before presenting it
### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests -- then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how
## Task Management
1. Plan First: Write plan to tasks/todo.md with checkable items
2. Verify Plan: Check in before starting implementation
3. Track Progress: Mark items complete as you go
4. Explain Changes: High-level summary at each step
5. Document Results: Add review section to tasks/todo.md
6. Capture Lessons: Update tasks/lessons.md after corrections
## Core Principles
- Simplicity First: Make every change as simple as possible. Impact minimal code.
- No Laziness: Find root causes. No temporary fixes. Senior developer standards.
- Minimal Impact: Only touch what's necessary. No side effects with new bugs.

