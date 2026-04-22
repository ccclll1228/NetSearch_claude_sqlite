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
config/settings.json (backupRoot + devices[])
        ↓  on startup + cron (05:00, 17:00)
server.js          — Express server, in-memory state, API routes
lib/discovery.js   — Resolves latest backup file per device at load time
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
- Calls `resolveDevicePaths()` at the start of `loadAllConfigs()` to get `[{path, type}]` from discovery; cron schedule comes from `config/settings.json`

### Discovery (`lib/discovery.js`)

- `resolveDevicePaths(devices, backupRoot)` — scans `{SITE}_{YYYYMMDD}` folders, newest first
- Site prefix derived from device name: `FRI-LTM01` → looks in `FRI_*` folders
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

### CSS Token System

All CSS variables use `--cds-*` (Carbon Design System) tokens. Key mapping from legacy names:

| Legacy | `--cds-*` token | Value |
|--------|----------------|-------|
| `--bg` | `--cds-background` | `#f4f4f4` |
| `--bg-card` | `--cds-layer-01` | `#ffffff` |
| `--bg-elevated` | `--cds-layer-02` | `#e0e0e0` |
| `--border` | `--cds-border-subtle` | `#c6c6c6` |
| `--text` | `--cds-text-primary` | `#161616` |
| `--text-secondary` | `--cds-text-secondary` | `#525252` |
| `--accent` | `--cds-interactive` | `#0f62fe` |
| `--accent-light` | `--cds-highlight` | `#edf5ff` |
| `--green` | `--cds-support-success` | `#24a148` |
| `--red` | `--cds-support-error` | `#da1e28` |
| `--radius` | `--cds-radius` | `0px` |
| `--font-ui` | `--cds-font-sans` | IBM Plex Sans |
| `--font-mono` | `--cds-font-mono` | IBM Plex Mono |

Do not introduce new ad-hoc CSS variables; always use `--cds-*` tokens.

### Configuration (`config/settings.json`)

```json
{
  "port": 3001,
  "backupRoot": "/home/oxidized/backups",
  "devices": [
    { "name": "FRI-LTM01", "type": "f5" },
    { "name": "FRI-FW01",  "type": "fortigate" }
  ],
  "fqdnFile": "/path/to/all_fqdn.csv",
  "cronSchedule": ["0 5 * * *", "0 17 * * *"]
}
```

- `backupRoot` — absolute path to the Oxidized backup root; discovery scans `{SITE}_{YYYYMMDD}` subfolders
- `devices[].name` — device identifier and filename prefix (e.g. `FRI-LTM01` matches `FRI-LTM01_*.txt`)
- `devices[].type` — passed through to the parser: `"f5"`, `"fortigate"`, `"paloalto"`, `"srx"`, `"auto"`
- `configFiles` — **removed**; replaced by `backupRoot + devices[]`

`config/settings.json` is gitignored. Use `config/settings.example.json` as the template.

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

### Duplicate Code Warning

`lib/parser.js` and `public/index.html` contain near-identical parser implementations. `lib/parser.js` is the server-side copy; the inline copy in `index.html` is used only for the drag-drop debug flow. If parsing logic changes, update both.


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

## Project Status (2026-04-22)

### Done
- [x] `git clone` — repo at `/home/local/SSO/yt0115/NetSearch_claude`
- [x] `npm install` — all dependencies installed
- [x] Server running via `npm run dev` on **port 3001** (port 3000 occupied by Grafana)
- [x] `config/settings.json` — updated to `backupRoot + devices[]` shape; 12 devices loading cleanly
- [x] `lib/discovery.js` — dynamic backup file discovery (newest folder, highest HHMM timestamp)
- [x] `config/settings.example.json` — updated to new shape

### TODO
- [ ] Set real `fqdnFile` path in `config/settings.json` once CSV location is known
- [ ] Test UI at http://localhost:3001
- [ ] Deploy (production: `npm start`)