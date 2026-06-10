# Changelog (Recent)

For the full changelog, see [CHANGELOG.md](../CHANGELOG.md) in the project root.

---

## [Unreleased]

### Added
- FQDN filter: search history dropdown (`localStorage`, max 10 unique entries)
- FQDN filter: clear (×) button inside input
- FQDN filter: dedicated Boolean Search `?` help popup
- FQDN filter: Boolean Search support (`NOT`/`AND`/`OR`/parentheses/`"quotes"`) via `evaluateAST()`
- FQDN filter: Enter-to-search only (no live filtering while typing)
- FQDN filter: input width increased by 50%
- Ignore CIDR toggle button with × (OFF) / ✓ (ON) icons replacing checkbox

### Changed
- EXACT/KEYWORD toggle embedded inside search bar as inline prefix (`.search-mode-btn` with 60%-height divider)
- EXACT/KEYWORD toggle: fixed 58px width, `var(--cds-font-mono)` 14px font matching input, single `#6c6a64` color, `border-bottom: 2px solid #6c6a64`, no re-render on click
- Brand title "NetSearch": `StyreneB/Inter` sans-serif 22px w600, removed "Config Visualizer" subtitle
- Toolbar buttons unified: 28px height, 6px gap, inline SVG icons, Bulk Search modal redesigned

### Fixed
- FortiGate poolname pill moved from APPLICATION column to DESTINATION column (DNAT-style)
- FortiGate poolname pill text wrapping (no longer truncated)
