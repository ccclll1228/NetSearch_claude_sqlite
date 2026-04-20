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
- `allRuleIps` is capped at 50 entries for routes/addresses/f5 chaining to prevent O(N×M) freeze on large groups
- `allRuleIpsForFqdn` is uncapped — CIDRs pre-converted to `{num,mask}` pairs for fast bitwise IP matching in FQDN tab
- `esc()` uses string replacement (not `createElement`) for HTML escaping
- Pill expand/collapse uses targeted DOM patching — never calls `renderContent()` for expand/collapse actions:
  - `_patchPillsChunked()` — rAF batches of 30 pills for Tab Expand/Collapse All (sec/nat)
  - `_patchPidsDirect(pids)` — synchronous patch for single rule card expand/collapse
  - `_findRootPid(pid)` — strips `__suffix` to locate top-level `_pillContext` entry for nested node toggle
  - `_patchGeneration` counter — cancels stale rAF loops when a new render/patch starts
- `_pillContext` Map (pid → `{item, type, parsed, ctx}`) and `_ruleExpandMap` (ruleKey → `{hostname, items, ctx}`) are populated during `renderPills()` and required by all DOM patch functions

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

### resolveObject() is flatten-only — never reuse for hierarchical output

`resolveObject()` expands all address groups to a **flat leaf list** (no depth metadata).
Use it for search/match scenarios only.

For any output that must preserve tree structure (copy text, tree rendering), write a
dedicated recursive walker that walks `groups[name]` directly, emitting each sub-group
name line **before** recursing into its members. See `tasks/lessons.md` for the pattern.

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