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

### Fixed
- FortiGate poolname pill moved from APPLICATION column to DESTINATION column (DNAT-style)
- FortiGate poolname pill text wrapping (no longer truncated)
