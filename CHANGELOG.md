# Changelog

All notable changes to NetSearch are documented here.

---

## [1.2.0] - 2026-04-05

### Added
- **Sticky column headers** — all tabs (Sec Rules, NAT Rules, Routes, FQDN, LTM, Pools) now freeze their column header row at `top:0` while scrolling through results. Backgrounds use solid `#141b2d` to prevent content bleed-through.
- **Objects tab: copy buttons** — each address row has a 📋 button (copies `name\tvalue`); each address group header has a 📋 button (copies group name + all members, one per line); each group member row has an individual 📋 button on hover.
- **Objects tab: full recursive tree** — expanding an address group now shows all nested sub-groups and their members in a fully-expanded tree (no additional clicks required). Uses `renderGroupTreeFull()` with circular reference guard (`_seen` Set, max depth 12).

### Changed
- **Expand / Collapse icons** — replaced `⊞`/`⊟` math symbols with SVG icons (four-corner expand / four-corner collapse) across all three locations: filter bar global buttons (`Expand` / `Collapse` labels added), per-rule buttons in Sec Rules card, and URL Category pill toggles. Previously used `➕`/`➖` emoji for URL Category.
- **Objects tab: address group members** — members now render in a vertical list (one per line) instead of horizontal pill wrap.
- **Objects tab: group expansion** — outer group toggle converted from DOM `classList.toggle` to `togglePill()` so that sub-group expansion (which calls `renderContent`) correctly preserves the outer group's open state.

### Fixed
- Sticky headers no longer overlap content — reverted accidental sticky on `.device-group-header` (device title bar) which caused z-index conflicts; only column header rows are sticky.
- `config/settings.json` Windows backslash paths replaced with forward slashes to fix `SyntaxError: Bad escaped character in JSON`.

---

## [1.1.0] - 2026-04-04

### Added
- **TAG badges** — security rules display tags below the rule name; NAT rules display tags beside the copy button. Font size is 50% of rule ID size (`6.5px`), styled as compact monospace chips.
- **NAT tab filters** — FROM ZONE, TO ZONE, and TAG filters now work correctly in the NAT Rules tab (previously only applied to Security Rules).
- **Tab-aware TAG dropdown** — switching to the NAT Rules tab populates the TAG filter with NAT rule tags; switching to Sec Rules tab shows security rule tags.
- **Zone dropdown includes NAT zones** — FROM ZONE / TO ZONE options now aggregate zones from both `secRules` and `natRules`.

### Changed
- **NAT column layout** — switched from fixed `px` widths to `fr` (fractional) units so columns fill the full container width at any screen size. Proportions now match Security Rules: `12fr 12fr 21fr 21fr 10fr 12fr 12fr`.
- **NAT column drag-resize** — resize math updated to convert `fr → px` using actual container width at drag start, giving intuitive pixel-accurate resizing.

---

## [1.0.0] - 2026-04-04

### Added — Backend (Phase 1 & 2)

- **Express server** (`server.js`) serving the frontend from `public/` and exposing three API endpoints:
  - `GET /api/data` — returns all parsed configs and FQDN records
  - `GET /api/status` — returns load status and per-device rule counts
  - `POST /api/reload` — triggers immediate config reload from disk
- **In-memory state** — `parsedConfigs[]`, `fqdnRecords[]`, `lastLoaded` held in process memory; served to all connected clients without re-parsing.
- **Disk cache** (`cache/parsed.json`) — written after every successful reload; read on server startup so the UI is immediately usable before the first parse completes.
- **Cron scheduler** (`lib/scheduler.js`) — auto-reloads configs on configurable cron expressions (default: `0 5 * * *` and `0 17 * * *`).
- **Config parsers extracted** to `lib/parser.js` — `parseConfig()` auto-detects device type; `parseFqdnFile()` parses CSV FQDN records.
- **Frontend data fetch** — `public/index.html` fetches from `GET /api/data` on load; falls back to empty state gracefully.
- **Port conflict error** — clear PowerShell command printed to console when port is already in use.

### Added — Frontend Improvements

- **Disabled rule styling** — disabled security and NAT rules are dimmed (`opacity: 0.38`, `grayscale(0.7)`). Rule name gains strikethrough. Hover restores partial visibility.
- **LTM expand/collapse fix** — ⊞/⊟ buttons now correctly operate `f5LtmExpandedRows` when on the LTM tab (previously modified the wrong state set).
- **LTM device group collapse fix** — ▶ header click now correctly matches `grp_${hostname}` key (previously used mismatched `grp_f5vs_` prefix).
- **NAT resizable columns** — sticky column header row with drag handles; columns resize independently without re-rendering rule cards.
- **SNAT/DNAT columns auto-show** — SNAT and DNAT columns only appear when at least one rule in the current result set has translation data.

### Performance

- **`allRuleIps` cap** — symmetric chaining IP set capped at 50 entries to prevent O(N×M) freeze when searching large address groups (e.g. 243-member groups).
- **`_matchNameOnly` cache** — `Map`-based cache added to recursive group name walk; cleared per `getFilteredData()` call.
- **`esc()` optimized** — HTML escaping switched from `createElement` (DOM allocation) to string `.replace()` chain.

---

## [0.1.0] - 2026-03-30 (Prototype)

- Single-file prototype (`NetSearch-prototype.html`) with all parsing and UI inline.
- FortiGate, Palo Alto, SRX, F5 config parsers.
- Boolean search engine with AST (`parseSearch`, `evaluateAST`).
- FQDN record lookup and IP chaining.
- Drag-and-drop config loading for local debug.
