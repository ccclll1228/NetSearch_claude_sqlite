# Changelog (Recent)

For the full changelog, see [CHANGELOG.md](../CHANGELOG.md) in the project root.

---

## [Unreleased] — 2026-06-15

### Added
- Full responsive layout support for all screen sizes (320px – 1920px)
- Mobile navbar: 2-row layout — logo + scrollable toolbar on row 1, search bar on row 2
- Horizontal scroll on Sec Rules and NAT Rules tables on mobile
- Tab bar horizontal scroll on narrow screens
- Filter rows use flex-wrap on mobile to prevent overflow
- Viewport meta tag added for correct mobile scaling
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
- EXACT/KEYWORD button height now matches toolbar buttons
- NetSearch brand text font unified with toolbar button font
- Mobile rule table min-width increased from 700px to 900px for wider, more readable columns
- Removed `overflow: hidden` from `.app` wrapper that blocked horizontal scroll on mobile
- Added `min-width` to `.rule-card` in mobile media query to prevent column compression
- Added right padding and `nowrap` to pills/tags to prevent clipping at scroll edge
- Search history dropdown not appearing on input focus — `overflow: hidden` on `.header-search` was clipping the absolute-positioned dropdown
- FortiGate poolname pill moved from APPLICATION column to DESTINATION column (DNAT-style)
- FortiGate poolname pill text wrapping (no longer truncated)
